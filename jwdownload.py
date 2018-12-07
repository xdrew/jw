import argparse
import json
import ssl
import os
from pathlib import Path
import re
import time
import urllib.request
from os import system, remove

BASE_DIR = '/app/'
DATA_DIR = '/data/'
SEGMENTS_FILE_PATH = os.getenv('SEGMENTS_FILE_PATH', DATA_DIR + 'meta/segments.json')
file_names = []
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def retry_download(func):
    def do_retry(self, curr_url, curr_file_path):
        attempts = 0
        while attempts < 10:
            # noinspection PyBroadException
            try:
                func(self, curr_url, curr_file_path)
                return
            except Exception:
                print('Retry {} in 10 seconds'.format(curr_url))
                attempts += 1
                time.sleep(10)
        remove(curr_file_path)
        raise Exception('Max retries exceeded ({}). Removing corrupted segment {}'.format(10, curr_file_path))

    return do_retry


class SegmentsAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if namespace.last_segment is not None:
            parser.error('Segments options cannot be used with last-segment')
        setattr(namespace, self.dest, values)


class JWDownloader:
    def __init__(self, **kwargs):
        self.output_file_name = re.search('/([^/]+\.mp4)/', kwargs['url']).group(1)
        self.url_parts = re.search('(.*/)(.*)$', kwargs['url'])
        self.url_pattern = self.url_parts.group(1) + '{}'
        self.name = self.cleanup_name(kwargs.get('name'))
        self.skip_cleanup = kwargs.get('skip_cleanup')
        self.last_segment = kwargs.get('last_segment')
        self.first_segment = kwargs.get('first_segment')
        self.total_segments = kwargs.get('total_segments')
        self.skip_downloaded = kwargs.get('skip_downloaded')

    def download(self):
        if self.skip_downloaded and os.path.exists(DATA_DIR + self.name):
            print('File {} already exists. To download it again run command without --skip-downloaded flag'.format(
                DATA_DIR + self.name))
            exit(0)
        self.download_segments()
        self.join_segments()
        self.convert_ts_to_mp4()
        if not self.skip_cleanup:
            self.cleanup()

    def get_last_segment(self, url):
        segments_lookup = self.get_segments_lookup()

        if self.last_segment is not None:
            segments_lookup[url] = self.last_segment
            print('Last segment id from last-segment arg {:d}'.format(segments_lookup[url]))
            return segments_lookup[url]

        if self.total_segments is not None:
            segments_lookup[url] = self.first_segment + self.total_segments - 1
            print('Last segment id from segments arg {:d}'.format(segments_lookup[url]))
            return segments_lookup[url]

        if url in segments_lookup:
            print('Last segment id from lookup {:d}'.format(segments_lookup[url]))
            return segments_lookup[url]

        segments_lookup[url] = self.get_last_index(url)
        self.save_segments_lookup(segments_lookup)
        print('Last segment id {:d}'.format(segments_lookup[url]))
        return segments_lookup[url]

    @staticmethod
    def save_segments_lookup(lookup):
        segments_file_dir = os.path.dirname(SEGMENTS_FILE_PATH)
        Path(segments_file_dir).mkdir(parents=True, exist_ok=True)
        with open(SEGMENTS_FILE_PATH, "w") as f:
            json.dump(lookup, f)

    @staticmethod
    def get_segments_lookup():
        segments_lookup = {}
        if os.path.exists(SEGMENTS_FILE_PATH):
            with open(SEGMENTS_FILE_PATH, "r") as f:
                segments_lookup = json.load(f)
        return segments_lookup

    def get_segment(self, segment_pattern, segment_idx, from_fs_segments_in_a_row):
        curr_file_path = (DATA_DIR + '{}_' + segment_pattern).format(self.output_file_name, segment_idx)
        curr_url = self.url_pattern.format(segment_pattern.format(segment_idx))
        if os.path.exists(curr_file_path):
            from_fs_segments_in_a_row.append(segment_idx)
            return curr_file_path
        self.print_segments_from_fs(from_fs_segments_in_a_row)
        from_fs_segments_in_a_row.clear()
        print('Downloading {}'.format(curr_url))
        self.download_segment(curr_url, curr_file_path)
        return curr_file_path

    @staticmethod
    def print_segments_from_fs(from_fs_segments_in_a_row):
        if len(from_fs_segments_in_a_row) == 1:
            print('Using segment {} from filesystem'.format(from_fs_segments_in_a_row[0]))
        elif len(from_fs_segments_in_a_row) > 1:
            print('Using segments from {} to {} from filesystem'.format(from_fs_segments_in_a_row[0],
                                                                        from_fs_segments_in_a_row[-1]))

    @retry_download
    def download_segment(self, curr_url, curr_file_path):
        try:
            with urllib.request.urlopen(curr_url, context=ctx) as u, open(curr_file_path, 'wb') as f:
                f.write(u.read())
        except KeyboardInterrupt:
            remove(curr_file_path)
            exit(1)

    def download_segments(self):
        segment_pattern = re.sub('\d+', '{}', self.url_parts.group(2))
        from_fs_segments_in_a_row = []
        for i in range(self.first_segment, self.get_last_segment(self.url_pattern.format(segment_pattern)) + 1):
            file_names.append(self.get_segment(segment_pattern, i, from_fs_segments_in_a_row))
        self.print_segments_from_fs(from_fs_segments_in_a_row)

    @staticmethod
    def get_code(url, idx):
        req = urllib.request.Request(url.format(idx), method='HEAD')
        try:
            with urllib.request.urlopen(req, context=ctx) as response:
                code = response.getcode()
        except urllib.error.HTTPError:
            code = 404

        print('HEAD request to segment {} ({:d})'.format(url.format(idx), code))
        return code

    def get_last_index(self, url, step=1000, skip=0):
        code = 200
        i = 1
        idx = step
        while code == 200:
            idx = i * step
            i += 1
            if skip and idx < skip:
                continue
            code = self.get_code(url, idx)
        if step == 1:
            return idx - step
        return self.get_last_index(url, int(step / 10), (idx - step) if idx != step else 0)

    def join_segments(self):
        print('Joining segments into a single .ts file')
        system('cat ' + "".join(['{} '.format(f) for f in file_names]) + '> {}'.format(
            DATA_DIR + self.output_file_name + '.ts'))
        print('Done')

    def convert_ts_to_mp4(self):
        print('Converting to mp4')
        system('avconv -y -i {}.ts -acodec copy -vcodec copy "{}"'.format(DATA_DIR + self.output_file_name,
                                                                          DATA_DIR + self.name))
        print('Done')

    def cleanup_name(self, name):
        if name is None:
            return self.output_file_name.lower()
        clean_name = re.sub(r'[\\/*?:"<>|]', "", name) + '.mp4'
        return clean_name.lower()

    def cleanup(self):
        print('Cleaning up')
        for chunk_file_name in file_names:
            remove(chunk_file_name)

        remove('{}.ts'.format(DATA_DIR + self.output_file_name))
        print('Done')


if __name__ == "__main__":
    args_parser = argparse.ArgumentParser(description='Download video in jwplayer format')
    args_parser.add_argument('url',
                             help='Url to parse link from (https://video.com/c/xxx.mp4/xxxxxxx/segment73.ts)')
    args_parser.add_argument('--name',
                             help='Output filename without extension ("Super video from www")',
                             required=False)
    args_parser.add_argument('--first-segment',
                             dest="first_segment",
                             default=1,
                             type=int,
                             help='First segment index (5)',
                             required=False)
    args_parser.add_argument('--last-segment',
                             dest="last_segment",
                             help='Last segment index (73)',
                             type=int,
                             required=False)
    args_parser.add_argument('--segments',
                             dest="total_segments",
                             help='Total segment amount to fetch. (73)',
                             type=int,
                             required=False,
                             action=SegmentsAction)
    args_parser.add_argument('--no-cleanup',
                             dest="skip_cleanup",
                             help='Do not delete segments',
                             required=False,
                             action='store_true')
    args_parser.add_argument('--skip-downloaded',
                             dest="skip_downloaded",
                             help='Do not process videos with existing output name',
                             required=False,
                             action='store_true')
    args = args_parser.parse_args()

    downloader = JWDownloader(**vars(args))
    downloader.download()

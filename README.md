jwdownloader
==============

A simple tool for downloading videos in jwplayer format

# Quick start

```bash
$ docker pull xdrew/jw
$ docker run --rm --name=jw -v `pwd`:/data xdrew/jw https://video.com/c/xxx.mp4/xxxxxxx/segment73.ts
```

# Parameters

```
usage: docker run --rm --name=jw -v `pwd`:/data xdrew/jw [-h] [--name NAME] [--first-segment FIRST_SEGMENT]
                     [--last-segment LAST_SEGMENT] [--segments TOTAL_SEGMENTS]
                     [--no-cleanup] [--skip-downloaded] [--chunk-file-name CHUNK_FILE_NAME]
                     url

Download video in jwplayer format

positional arguments:
  url                   Url to parse link from
                        (https://video.com/c/xxx.mp4/xxxxxxx/segment73.ts)

optional arguments:
  -h, --help            show this help message and exit
  --name NAME           Output filename without extension ("Super video from www")
  --first-segment FIRST_SEGMENT
                        First segment index (5)
  --last-segment LAST_SEGMENT
                        Last segment index (73)
  --segments TOTAL_SEGMENTS
                        Total segment amount to fetch. (73)
  --chunk-file-name CHUNK_FILE_NAME
                        Custom chunk file name (my_video.mp4)
  --no-cleanup          Do not delete segments
  --skip-downloaded     Do not process videos with existing output name
```

# Hints

It's convenient to have an alias for this command

```bash
$ echo 'alias jw="docker run --rm --name=jw -v `pwd`:/data xdrew/jw"' >> ~/.bashrc && source ~/.bashrc
```

Sometimes it's handy to put multiple videos into queues
```bash
$ cat queue.sh
jw https://video.com/c/xxxx.mp4/asdf/segment1.ts --name="Video 1"
jw https://video.com/c/yyyy.mp4/adsf/segment1.ts --name="Video 2"
```

To make alias work inside this queue file you can do the following
```bash
echo "function jw() {
    docker run --rm --name=jw -v \`pwd\`:/data xdrew/jw \"\$@\"
} 
export -f jw" >> ~/.bashrc && source ~/.bashrc
```

And just run the queue
```bash
./queue.sh
```
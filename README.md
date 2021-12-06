# Markdown articles tool

Forked from https://github.com/artiomn/markdown_articles_tool.

This tool can
- Download markdown article with images and replace image links.  
  - Find all links to images, download images and fix links in the document.
  - Similar images may be deduplicated by content hash.
- Convert Markdown documents to:
  * HTML.
  * PDF.


## Usage

Syntax:

```
usage: markdown_tool.py [-h] [--version]
                        [--encoding ENCODING]
                        [-s SKIP_LIST] 
                        [-d IMAGES_DIRNAME]
                        [--use-article-name-as-images-dir]
                        [-p IMAGES_PUBLIC_DIR]
                        [-a --skip-all-incorrect] 
                        [--skip-on-existing-filename]
                        [-t DOWNLOADING_TIMEOUT]
                        [-D --dedup-with-hash]
                        [-R --remove-source]
                        [-O {md,html,pdf}]
                        [--output-path OUTPUT_PATH]
                        article_file_path_or_url

Simple script to download images and replace image links in markdown
documents.

positional arguments:
  article_file_path_or_url
                        path to the article file in the Markdown format

optional arguments:
  -h, --help            show this help message and exit
  --encoding ENCODING   File encoding.
  -s SKIP_LIST, --skip-list SKIP_LIST
                        skip URL's from the comma-separated list (or file with
                        a leading '@')
  -d IMAGES_DIRNAME, --images-dirname IMAGES_DIRNAME
                        Relative directory name to the output path to store
                        images
  --use-article-name-as-images-dir
                        Use article file name as the folder name to store
                        images, will override "--images-dir-name"
  -p IMAGES_PUBLIC_DIR, --images-public-dir IMAGES_PUBLIC_DIR
                        Absolute path to store all images, will override "--
                        images-dirname" and "--use-article-name-as-images-dir"
  -a, --skip-all-incorrect
                        skip all incorrect images
  --skip-on-existing-filename
                        skip on existing filename
  -t DOWNLOADING_TIMEOUT, --downloading-timeout DOWNLOADING_TIMEOUT
                        how many seconds to wait before downloading will be
                        failed
  -D, --dedup-with-hash
                        Deduplicate images, using content hash
  -R, --remove-source   Remove or replace source file
  -O {md,html}, --output-format {md,html}
                        output format
  --output-path OUTPUT_PATH
                        article output file name
  --version             return version number
```

Example:

```
./markdown_tool.py nc-1-zfs/article.md
```

Example 2:

```
./markdown_tool.py not-nas/sov/article.md -O html -s "http://www.ossec.net/_images/ossec-arch.jpg" -a
```

Example 3 (run on a folder):

```
find content/ -name "*.md" | xargs -n1 ./markdown_tool.py
```

## Notes
- This tool will only download image links with native Markdown syntax, i.e. images linked with HTML "\<img\>" tags will not be downloaded.

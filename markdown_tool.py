#!/usr/bin/python3

"""
Simple script to download images and replace image links in markdown documents.
"""

import argparse
import os

from mimetypes import types_map
from pathlib import Path
from time import strftime

from pkg.formatters.html import HTMLFormatter
from pkg.formatters.simple import SimpleFormatter
from pkg.image_downloader import ImageDownloader
from pkg.transformers.md.transformer import ArticleTransformer
from pkg.www_tools import is_url, get_base_url, get_filename_from_url, download_from_url

try:
    from pkg.formatters.pdf import PDFFormatter
except ModuleNotFoundError:
    PDFFormatter = None


__version__ = '0.0.4'
FORMATTERS = [SimpleFormatter, HTMLFormatter, PDFFormatter]
del types_map['.jpe']


def main(arguments):
    """
    Entrypoint.
    """

    print(f'Markdown tool version {__version__} started...')

    article_link = arguments.article_file_path_or_url
    if is_url(article_link):
        timeout = arguments.downloading_timeout
        if timeout < 0:
            timeout = None
        response = download_from_url(article_link, timeout=timeout)
        article_path_str = get_filename_from_url(response)

        with open(article_path_str, 'wb') as article_file:
            article_file.write(response.content)
            article_file.close()
    else:
        response = None
        article_path_str = os.path.expanduser(article_link)
    print(f'File "{article_path_str}" will be processed...')
    article_path = Path(article_path_str)

    formatter = [f for f in FORMATTERS if f is not None and f.format == arguments.output_format]
    assert len(formatter) == 1
    formatter = formatter[0]

    article_output_path = Path(arguments.output_path) if arguments.output_path else article_path.parent.joinpath(
        f'{article_path.stem}.{formatter.format}')

    skip_list = arguments.skip_list
    if isinstance(skip_list, str):
        if skip_list.startswith('@'):
            skip_list = skip_list[1:]
            print(f'Reading skip list from a file "{skip_list}"...')
            with open(os.path.expanduser(skip_list), 'r') as fsl:
                skip_list = [s.strip() for s in fsl.readlines()]
        else:
            skip_list = [s.strip() for s in skip_list.split(',')]

    images_dir = article_output_path.parent.joinpath(
        article_path.stem if arguments.use_article_name_as_images_dir else arguments.images_dirname)

    img_downloader = ImageDownloader(
        images_dir=images_dir,
        article_base_url=get_base_url(response),
        skip_list=skip_list,
        skip_all_errors=arguments.skip_all_incorrect,
        img_public_dir=arguments.images_public_dir,
        downloading_timeout=arguments.downloading_timeout,
        deduplication=arguments.dedup_with_hash,
        skip_on_existing_filename=arguments.skip_on_existing_filename,
    )

    result = ArticleTransformer(article_path, img_downloader, encoding=arguments.encoding).run()

    if article_output_path.is_file():
        article_output_basename = f'{article_path.stem}_{strftime("%Y%m%d_%H%M%S")}.{formatter.format}'
        article_output_path = article_path.parent.joinpath(article_output_basename)
    print(f'Writing file into "{str(article_output_path)}"...')

    with open(article_output_path, 'wb') as outfile:
        outfile.write(formatter.write(result))

    if arguments.remove_source and article_path.is_file():
        print(f'Removing source file "{article_path_str}"...')
        os.remove(article_path)

    print('Processing finished successfully...')


if __name__ == '__main__':
    out_format_list = [f.format for f in FORMATTERS if f is not None]

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('article_file_path_or_url', type=str,
                        help='path to the article file in the Markdown format')
    parser.add_argument('--encoding', type=str, default=None, help='File encoding.')
    parser.add_argument('-s', '--skip-list', default=None,
                        help='skip URL\'s from the comma-separated list (or file with a leading \'@\')')
    parser.add_argument('-d', '--images-dirname', type=str, default='images',
                        help='Relative directory name to the output path to store images')
    parser.add_argument('--use-article-name-as-images-dir', default=False, action='store_true',
                        help=('Use article file name as the folder name to store images, '
                              'will override "--images-dir-name"'))
    parser.add_argument('-p', '--images-public-dir', type=str, default='',
                        help=('Absolute path to store all images, '
                              'will override "--images-dirname" and "--use-article-name-as-images-dir"'))
    parser.add_argument('-a', '--skip-all-incorrect', default=False, action='store_true',
                        help='skip all incorrect images')
    parser.add_argument('--skip-on-existing-filename', default=False, action='store_true',
                        help='skip on existing filename')
    parser.add_argument('-t', '--downloading-timeout', type=float, default=-1,
                        help='how many seconds to wait before downloading will be failed')
    parser.add_argument('-D', '--dedup-with-hash', default=False, action='store_true',
                        help='Deduplicate images, using content hash')
    parser.add_argument('-R', '--remove-source', default=False, action='store_true',
                        help='Remove or replace source file')
    parser.add_argument('-O', '--output-format', default=out_format_list[0], choices=out_format_list,
                        help='output format')
    parser.add_argument('--output-path', type=str, help='article output file name')
    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}', help='return version number')

    args = parser.parse_args()

    main(args)

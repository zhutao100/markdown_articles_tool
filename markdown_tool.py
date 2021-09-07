#!/usr/bin/python3

"""
Simple script to download images and replace image links in markdown documents.
"""

import argparse
import os

from time import strftime
from mimetypes import types_map

from pkg.transformers.md.transformer import ArticleTransformer
from pkg.image_downloader import ImageDownloader
from pkg.www_tools import is_url, get_base_url, get_filename_from_url, download_from_url
from pkg.formatters.simple import SimpleFormatter
from pkg.formatters.html import HTMLFormatter

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
        article_path = get_filename_from_url(response)

        with open(article_path, 'wb') as article_file:
            article_file.write(response.content)
            article_file.close()
    else:
        response = None
        article_path = os.path.expanduser(article_link)
    print(f'File "{article_path}" will be processed...')

    formatter = [f for f in FORMATTERS if f is not None and f.format == arguments.output_format]
    assert len(formatter) == 1
    formatter = formatter[0]
    article_file_name = os.path.splitext(article_path)[0]
    article_output_path = arguments.output_path if arguments.output_path else f'{article_file_name}.{formatter.format}'

    skip_list = arguments.skip_list
    if isinstance(skip_list, str):
        if skip_list.startswith('@'):
            skip_list = skip_list[1:]
            print(f'Reading skip list from a file "{skip_list}"...')
            with open(os.path.expanduser(skip_list), 'r') as fsl:
                skip_list = [s.strip() for s in fsl.readlines()]
        else:
            skip_list = [s.strip() for s in skip_list.split(',')]

    images_dir = os.path.join(os.path.dirname(article_output_path), os.path.splitext(os.path.basename(article_path))[0]
                              if arguments.use_article_name_as_images_dir else arguments.images_dirname)
    img_downloader = ImageDownloader(
        images_dir=images_dir,
        article_base_url=get_base_url(response),
        skip_list=skip_list,
        skip_all_errors=arguments.skip_all_incorrect,
        img_public_dir=arguments.images_public_dir,
        downloading_timeout=arguments.downloading_timeout,
        deduplication=arguments.dedup_with_hash
    )

    result = ArticleTransformer(article_path, img_downloader, encoding=arguments.encoding).run()

    if article_path == article_output_path and not arguments.remove_source:
        article_output_path = f'{article_file_name}_{strftime("%Y%m%d_%H%M%S")}.{formatter.format}'
    print(f'Writing file into "{article_output_path}"...')

    with open(article_output_path, 'wb') as outfile:
        outfile.write(formatter.write(result))

    if arguments.remove_source and article_path != article_output_path:
        print(f'Removing source file "{article_path}"...')
        os.remove(article_path)

    print('Processing finished successfully...')


if __name__ == '__main__':
    out_format_list = [f.format for f in FORMATTERS if f is not None]

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('article_file_path_or_url', type=str,
                        help='path to the article file in the Markdown format')
    parser.add_argument('--encoding', default=None, help='File encoding.')
    parser.add_argument('-s', '--skip-list', default=None,
                        help='skip URL\'s from the comma-separated list (or file with a leading \'@\')')
    parser.add_argument('-d', '--images-dirname', default='images',
                        help='Relative directory name to the output path to store images')
    parser.add_argument('--use-article-name-as-images-dir', default=False, action='store_true',
                        help=('Use article file name as the folder name to store images, '
                              'will override "--images-dir-name"'))
    parser.add_argument('-p', '--images-public-dir', default='',
                        help=('Absolute path to store all images, '
                              'will override "--images-dirname" and "--use-article-name-as-images-dir"'))
    parser.add_argument('-a', '--skip-all-incorrect', default=False, action='store_true',
                        help='skip all incorrect images')
    parser.add_argument('-t', '--downloading-timeout', type=float, default=-1,
                        help='how many seconds to wait before downloading will be failed')
    parser.add_argument('-D', '--dedup-with-hash', default=False, action='store_true',
                        help='Deduplicate images, using content hash')
    parser.add_argument('-R', '--remove-source', default=False, action='store_true',
                        help='Remove or replace source file')
    parser.add_argument('-o', '--output-format', default=out_format_list[0], choices=out_format_list,
                        help='output format')
    parser.add_argument('--output-path', type=str, help='article output file name')
    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}', help='return version number')

    args = parser.parse_args()

    main(args)

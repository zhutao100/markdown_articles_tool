#!/usr/bin/python3

"""
Simple script to download images and replace image links in markdown documents.
"""

import argparse

from io import StringIO
from itertools import permutations
from mimetypes import types_map
from pathlib import Path
from time import strftime
from typing import List

from pkg.formatters.html import HTMLFormatter
from pkg.formatters.simple import SimpleFormatter
from pkg.image_downloader import ImageDownloader
from pkg.transformers.md.transformer import ArticleTransformer as MarkdownArticleTransformer
from pkg.transformers.html.transformer import ArticleTransformer as HTMLArticleTransformer
from pkg.www_tools import is_url, get_base_url, get_filename_from_url, download_from_url

try:
    from pkg.formatters.pdf import PDFFormatter
except ModuleNotFoundError:
    PDFFormatter = None


__version__ = '0.0.7'
TRANSFORMERS = [MarkdownArticleTransformer, HTMLArticleTransformer]
FORMATTERS = [SimpleFormatter, HTMLFormatter, PDFFormatter]
del types_map['.jpe']


def transform_article(article_path: str, input_format_list: List[str],
                      img_downloader: ImageDownloader, encoding: str) -> str:
    """
    Download images and fix URL's.
    """
    transformers = [tr for ifmt in input_format_list
                    for tr in TRANSFORMERS if tr is not None and tr.format == ifmt]

    with open(article_path, 'r', encoding=encoding) as article_file:
        result = StringIO(article_file.read())

    for transformer in transformers:
        lines = transformer(result, img_downloader).run()
        result = StringIO(''.join(lines))

    return result.read()


def get_formatter(output_format: str):
    formatter = [f for f in FORMATTERS if f is not None and f.format == output_format]
    assert len(formatter) == 1
    formatter = formatter[0]

    return formatter


def get_article_output_path(article_path: Path, explicit_output_path: Path,
                            file_format: str, remove_source: bool, output_postfix: str = '') -> Path:
    article_output_stem = article_path.stem.replace(' ', '_')
    if explicit_output_path:
        article_output_path = Path(explicit_output_path)
    else:
        article_output_basename = f'{article_output_stem}{output_postfix}.{file_format}'
        article_output_path = article_path.parent.joinpath(article_output_basename)
        if article_output_path.is_file() and not remove_source:
            article_output_basename = f'{article_output_stem}_{strftime("%Y%m%d_%H%M%S")}.{file_format}'
            article_output_path = article_path.parent.joinpath(article_output_basename)

    return article_output_path


def format_article(article_out_path: str, article_text: str, formatter) -> None:
    """
    Save article in the selected format.
    """

    print(f'Writing file into "{article_out_path}"...')

    with open(article_out_path, 'wb') as outfile:
        outfile.write(formatter.write(article_text))


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
        article_path = Path(get_filename_from_url(response))

        with open(article_path, 'wb') as article_file:
            article_file.write(response.content)
            article_file.close()
    else:
        response = None
        article_path = Path(article_link).expanduser()
    print(f'File "{article_path}" will be processed...')

    article_formatter = get_formatter(arguments.output_format)
    article_output_path = get_article_output_path(article_path, arguments.output_path,
                                                  article_formatter.format, arguments.remove_source,
                                                  output_postfix=arguments.output_postfix)
    print(f'The new file will be save to "{article_output_path}"...')

    skip_list = arguments.skip_list
    if isinstance(skip_list, str):
        if skip_list.startswith('@'):
            skip_list = skip_list[1:]
            print(f'Reading skip list from a file "{skip_list}"...')
            with open(Path(skip_list).expanduser(), 'r') as fsl:
                skip_list = [s.strip() for s in fsl.readlines()]
        else:
            skip_list = [s.strip() for s in skip_list.split(',')]

    if str(arguments.images_public_dir):
        images_dir = Path(arguments.images_public_dir)
    else:
        images_dir = article_output_path.parent.joinpath(
            article_output_path.stem if arguments.use_article_name_as_images_dir else arguments.images_dirname)

    img_downloader = ImageDownloader(
        images_dir=images_dir,
        article_base_url=get_base_url(response),
        skip_list=skip_list,
        skip_all_errors=arguments.skip_all_incorrect,
        downloading_timeout=arguments.downloading_timeout,
        deduplication=arguments.dedup_with_hash,
        skip_on_existing_filename=arguments.skip_on_existing_filename,
        overwrite=arguments.overwrite,
    )

    result = transform_article(article_path, arguments.input_format.split('+'), img_downloader, arguments.encoding)

    format_article(article_output_path, result, article_formatter)

    if arguments.remove_source and article_path.is_file():
        print(f'Removing source file "{article_path}"...')
        article_path.unlink()

    print('Processing finished successfully...')


if __name__ == '__main__':
    in_format_list = [f.format for f in TRANSFORMERS if f is not None]
    in_format_list = [*in_format_list, *('+'.join(i) for i in permutations(in_format_list))]
    out_format_list = [f.format for f in FORMATTERS if f is not None]

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('article_file_path_or_url', type=str,
                        help='path to the article file in the Markdown format')
    parser.add_argument('-a', '--skip-all-incorrect', default=False, action='store_true',
                        help='skip all incorrect images')
    parser.add_argument('-d', '--images-dirname', type=str, default='images',
                        help='Relative directory name to the output path to store images')
    parser.add_argument('-f', '--overwrite', default=False, action='store_true',
                        help='Overwrite existing files')
    parser.add_argument('-o', '--output-path', type=str,
                        help=('specified article output file name; ', 'will override "--output-postfix"'))
    parser.add_argument('-p', '--images-public-dir', type=str, default='',
                        help=('Absolute path to store all images; '
                              'will override "--images-dirname" and "--use-article-name-as-images-dir"; '
                              'note that output file will still use relative paths in light of markdown portability.'))
    parser.add_argument('-s', '--skip-list', default=None,
                        help='skip URL\'s from the comma-separated list (or file with a leading \'@\')')
    parser.add_argument('-t', '--downloading-timeout', type=float, default=-1,
                        help='how many seconds to wait before downloading will be failed')
    parser.add_argument('-D', '--dedup-with-hash', default=False, action='store_true',
                        help='Deduplicate images, using content hash')
    parser.add_argument('-I', '--input-format', default='md', choices=in_format_list,
                        help='input format')
    parser.add_argument('-O', '--output-format', default=out_format_list[0], choices=out_format_list,
                        help='output format')
    parser.add_argument('-R', '--remove-source', default=False, action='store_true',
                        help='Remove or replace source file')
    parser.add_argument('--encoding', type=str, default='UTF-8',
                        help='File encoding.')
    parser.add_argument('--output-postfix', type=str, default='-local',
                        help='postfix for article output file name')
    parser.add_argument('--skip-on-existing-filename', default=False, action='store_true',
                        help='skip on existing filename')
    parser.add_argument('--use-article-name-as-images-dir', default=False, action='store_true',
                        help=('Use article file name as the folder name to store images, '
                              'will override "--images-dir-name"'))
    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}',
                        help='return version number')

    args = parser.parse_args()

    main(args)

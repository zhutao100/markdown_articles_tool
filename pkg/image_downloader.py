import hashlib
import os

from collections import OrderedDict
from pathlib import Path
from time import strftime
from typing import Optional, List

from pkg.www_tools import is_url, get_filename_from_url, download_from_url


class ImageDownloader:
    """
    "Smart" images downloader.
    """

    def __init__(self, images_dir: os.PathLike,
                 article_base_url: str = '',
                 skip_list: Optional[List[str]] = None,
                 downloading_timeout: float = -1,
                 skip_all_errors: bool = False,
                 deduplication: bool = False,
                 skip_on_existing_filename: bool = False,
                 overwrite: bool = False):
        self._images_dir = Path(images_dir)
        self._article_base_url = article_base_url
        self._skip_list = set(skip_list) if skip_list is not None else []
        self._skip_all_errors = skip_all_errors
        self._downloading_timeout = downloading_timeout if downloading_timeout > 0 else None
        self._deduplication = deduplication
        self._skip_on_existing_filename = skip_on_existing_filename
        self._overwrite = overwrite

    def download_images(self, images: List[str]) -> dict:
        """
        Download and save images from the list.

        :return URL -> file path mapping.
        """
        self._images_dir.mkdir(parents=True, exist_ok=True)

        replacement_mapping = {}
        hash_to_path_mapping = {}
        for img_num, img_url in enumerate(images):
            assert img_url not in replacement_mapping.keys(), f'BUG: already downloaded image "{img_url}"...'

            if img_url in self._skip_list:
                print(f'Image {img_num + 1} ["{img_url}"] was skipped, because it\'s in the skip list...')
                continue

            if self._skip_on_existing_filename:
                potential_filename = img_url.rsplit('/', 1)[1]
                real_img_path = self._images_dir.joinpath(potential_filename)
                try:
                    if real_img_path.is_file():
                        document_img_path = Path(self._images_dir.name, potential_filename)
                        replacement_mapping.setdefault(img_url, document_img_path)
                        print(f'Image {img_num + 1} ["{img_url}"] is skipped since there is an existing file...')
                        continue
                except OSError:
                    pass

            if not is_url(img_url):
                print(f'Image {img_num + 1} ["{img_url}"] has incorrect URL...')
                if self._article_base_url:
                    print(f'Trying to add base URL "{self._article_base_url}"...')
                    img_url = f'{self._article_base_url}/{img_url}'
                else:
                    print('Image downloading will be skipped...')
                    continue

            print(f'Downloading image {img_num + 1} of {len(images)} from "{img_url}"...')

            try:
                img_response = download_from_url(img_url, self._downloading_timeout)
            except Exception as e:
                if self._skip_all_errors:
                    print(f'Warning: can\'t download image {img_num + 1}, error: [{str(e)}], '
                          'but processing will be continued, because `skip_all_errors` flag is set')
                    continue
                raise

            img_filename = get_filename_from_url(img_response)
            image_content = img_response.content

            if self._deduplication:
                new_content_hash = hashlib.sha256(image_content).digest()
                existing_img_filename = hash_to_path_mapping.get(new_content_hash)
                if existing_img_filename is not None:
                    document_img_path = Path(self._images_dir.name, existing_img_filename)
                    replacement_mapping.setdefault(img_url, document_img_path)
                    continue
                else:
                    hash_to_path_mapping[new_content_hash] = img_filename

            img_filename = self._get_unique_imge_filename(replacement_mapping, img_url, img_filename)

            real_img_path = self._images_dir.joinpath(img_filename)
            if real_img_path.is_file() and not self._overwrite:
                img_filename = f'{real_img_path.stem}_{strftime("%Y%m%d_%H%M%S")}{real_img_path.suffix}'
                real_img_path = self._images_dir.joinpath(img_filename)

            document_img_path = Path(self._images_dir.name, img_filename)
            replacement_mapping.setdefault(img_url, document_img_path)

            ImageDownloader._write_image(real_img_path, image_content)

        return OrderedDict(sorted(replacement_mapping.items(), reverse=True))

    @staticmethod
    def _write_image(img_path: os.PathLike, data: bytes):
        """
        Write image data into the file.
        """

        print(f'Image is saved to "{str(img_path)}"...')
        with open(img_path, 'wb') as img_file:
            img_file.write(data)
            img_file.close()

    def _get_unique_imge_filename(self, replacement_mapping, img_url, img_filename):
        """
        Fix path if a file with the similar name exists already.
        """

        document_img_path = Path(self._images_dir.name, img_filename)
        # Images can have similar names but different URLs, here we'd like to save the original filenames if possible.
        for url, path in replacement_mapping.items():
            if document_img_path == path and img_url != url:
                img_filename = (f'{document_img_path.stem}_'
                                f'{hashlib.md5(img_url.encode()).hexdigest()}{document_img_path.suffix}')
                break

        return img_filename

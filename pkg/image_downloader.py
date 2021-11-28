import os
import hashlib
from typing import Optional, List

from .www_tools import is_url, get_filename_from_url, download_from_url


class ImageDownloader:
    """
    "Smart" images downloader.
    """

    def __init__(self, images_dir: str, article_base_url: str = '', skip_list: Optional[List[str]] = None,
                 skip_all_errors: bool = False, img_public_dir: str = '',
                 downloading_timeout: float = -1, deduplication: bool = False, skip_on_existing_filename: bool = False):
        self._images_dir = images_dir
        self._img_dir_name = os.path.basename(images_dir)
        self._img_public_dir = img_public_dir
        self._article_base_url = article_base_url
        self._skip_list = set(skip_list) if skip_list is not None else []
        self._skip_all_errors = skip_all_errors
        self._downloading_timeout = downloading_timeout if downloading_timeout > 0 else None
        self._deduplication = deduplication
        self._skip_on_existing_filename = skip_on_existing_filename

    def download_images(self, images: List[str]) -> dict:
        """
        Download and save images from the list.

        :return URL -> file path mapping.
        """

        replacement_mapping = {}
        hash_to_path_mapping = {}
        skip_list = self._skip_list
        img_count = len(images)
        path_join = os.path.join
        img_dir_name = self._img_dir_name
        img_public_dir = self._img_public_dir
        images_dir = self._images_dir
        deduplication = self._deduplication

        os.makedirs(self._images_dir, exist_ok=True)

        for img_num, img_url in enumerate(images):
            assert img_url not in replacement_mapping.keys(), f'BUG: already downloaded image "{img_url}"...'

            if img_url in skip_list:
                print(f'Image {img_num + 1} ["{img_url}"] was skipped, because it\'s in the skip list...')
                continue

            if self._skip_on_existing_filename:
                potential_file_name = img_url.rsplit('/', 1)[1]
                if os.path.isfile(os.path.join(self._images_dir, potential_file_name)):
                    print(f'Image {img_num + 1} ["{img_url}"] is skipped since there is an existing file...')
                    continue

            if not is_url(img_url):
                print(f'Image {img_num + 1} ["{img_url}"] has incorrect URL...')
                if self._article_base_url:
                    print(f'Trying to add base URL "{self._article_base_url}"...')
                    img_url = f'{self._article_base_url}/{img_url}'
                else:
                    print('Image downloading will be skipped...')
                    continue

            print(f'Downloading image {img_num + 1} of {img_count} from "{img_url}"...')

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

            if deduplication:
                new_content_hash = hashlib.sha256(image_content).digest()
                existed_file_name = hash_to_path_mapping.get(new_content_hash)
                if existed_file_name is not None:
                    img_filename = existed_file_name
                    document_img_path = path_join(img_public_dir or img_dir_name, img_filename)
                    replacement_mapping.setdefault(img_url, document_img_path)
                    continue
                else:
                    hash_to_path_mapping[new_content_hash] = img_filename

            document_img_path = path_join(img_public_dir or img_dir_name, img_filename)
            img_filename, document_img_path = self._correct_paths(replacement_mapping, document_img_path, img_url,
                                                                  img_filename)

            real_img_path = path_join(img_public_dir or images_dir, img_filename)
            replacement_mapping.setdefault(img_url, document_img_path)

            ImageDownloader._write_image(real_img_path, image_content)

        return replacement_mapping

    @staticmethod
    def _write_image(img_path: str, data: bytes):
        """
        Write image data into the file.
        """

        print(f'Image will be written to the file "{img_path}"...')
        with open(img_path, 'wb') as img_file:
            img_file.write(data)
            img_file.close()

    def _correct_paths(self, replacement_mapping, document_img_path, img_url, img_filename):
        """
        Fix path if a file with the similar name exists already.
        """

        # Images can have similar name, but different URLs, but I want to save original filename, if possible.
        for url, path in replacement_mapping.items():
            if document_img_path == path and img_url != url:
                img_filename = f'{hashlib.md5(img_url.encode()).hexdigest()}_{img_filename}'
                document_img_path = os.path.join(self._img_public_dir or self._img_dir_name, img_filename)
                break

        return img_filename, document_img_path

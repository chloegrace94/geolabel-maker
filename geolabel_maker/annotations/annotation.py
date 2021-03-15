# Encoding: UTF-8
# File: annotation.py
# Creation: Sunday February 7th 2021
# Supervisor: Daphné Lercier (dlercier)
# Author: Arthur Dujardin (arthurdjn)
# ------
# Copyright (c) 2021, Makina Corpus


r"""
This module defines the architecture of an annotations constructor.
In *Geolabel Maker*, you can create your annotations file with different constructors such as:

- :class:`~geolabel_maker.annotations.object_detection.ObjectDetection`: for object detections,
- :class:`~geolabel_maker.annotations.classification.Classification`: for image classification.
- :class:`~geolabel_maker.annotations.segmentation.Segmentation`: for instance segmentation,

These constructors can then be used to save your annotations to a file. 
The supported formats are JSON, TXT or CSV, depending on the constructors used.

Also, two methods can be used to generate annotations:

- :class:`~geolabel_maker.annotations.annotation.Annotation.make`: requires only categories and images,
- :class:`~geolabel_maker.annotations.annotation.Annotation.build`: fast but requires masks (a.k.a labels).
"""


# Basic imports
from abc import ABC, abstractmethod
from tqdm import tqdm
from datetime import datetime
from copy import deepcopy
from PIL import Image

# Geolabel Maker
from geolabel_maker.utils import relative_path
from ._utils import get_paths, get_categories


__all__ = [
    "Annotation"
]


def _check_value(value):
    if not isinstance(value, dict):
        raise ValueError(f"The value must be a dict. Got '{type(value).__name__}'.")


def _check_values(values):
    if not isinstance(values, (list, tuple)):
        raise ValueError(f"The values must be a list of dictionaries. Got '{type(values).__name__}'.")

    for value in values:
        _check_value(value)


class Annotation(ABC):
    """
    Abstract architecture used to wrap all annotations.
    This class is used to wrap annotation constructors for segmentation, object detection and classification.

    * :attr:`images` (list): List of dictionaries containing meta information of the images.

    * :attr:`categories` (list): List of dictionaries containing meta information of the categories.

    * :attr:`annotations` (list): List of dictionaries containing the detail of the annotations (seg).

    """

    def __init__(self, images=None, categories=None, annotations=None, info=None):
        images = images or []
        categories = categories or []
        annotations = annotations or []
        info = info or {
            "description": "Auto-generated by Geolabel-Maker",
            "date_created": datetime.now().strftime("%Y/%m/%d")
        }
        _check_values(images)
        _check_values(categories)
        _check_values(annotations)
        _check_value(info)
        self.images = images
        self.categories = categories
        self.annotations = annotations
        self.info = info

    @classmethod
    @abstractmethod
    def open(cls, filename, **kwargs):
        """Open an annotation from a file name.

        Args:
            filename (str): Name of the annotation to open.
            kwargs (dict): Remaining arguments.

        Returns:
            Annotation
        """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def build_annotations(cls, images=None, categories=None, labels=None,
                          dir_images=None, dir_labels=None, colors=None,
                          pattern="*", **kwargs):
        """Build only the annotations details.
        This method requires images, masks, and colors. Note that categories are optional,
        as only their name and color are used during the process.
        Therefore to avoid loading expensive data in memory, 
        you can simply specify categories names and colors through the ``colors`` argument.
        Although this method is fast, it is not precise for small scales:
        the objects are not clearly separated in a mask, and some are merged.
        
        .. seealso::
            If you want to create precise annotations, 
            use ``make_annotations`` method.

        Args:
            images (list, optional): List of image paths to be used. Defaults to ``None``.
            categories (list, optional): List of loaded categories to be used. Defaults to ``None``.
            labels (list, optional): List of mask paths to be used. Defaults to ``None``.
            dir_images (str, optional): Path to the directory containing images to be used. Defaults to ``None``.
            dir_labels (str, optional): Path to the directory containing masks to be used. Defaults to ``None``.
            colors (dict, optional): Dictionary of ``{name: color}`` associated to the categories. 
                Here ``name`` refers to a category's name and ``color`` its color. Defaults to ``None``.
            pattern (str, optional): Pattern used to retrieve images and masks. Defaults to ``"*"``.
            kwargs (dict, optional): Remaining arguments.

        Returns:
            list: A list of dictionaries containing the annotations' details.
        """
        raise NotImplementedError

    @classmethod
    def build_categories(cls, categories=None, colors=None, **kwargs):
        """Build only the categories details.
        This method requires images, masks, and colors. Note that categories are optional,
        as only their names and colors are used during the process.
        Therefore to avoid loading expensive data in memory, 
        you can simply specify categories' names and colors through the ``colors`` argument.
        
        .. seealso::
            If you want to create precise annotations, 
            use ``make_categories`` method.
    
        Args:
            categories (list, optional): List of loaded categories to be used. Defaults to ``None``.
            colors (dict, optional): Dictionary of ``{name: color}`` associated to the categories. 
                Here ``name`` refers to a category's name and ``color`` its color. Defaults to ``None``.
            kwargs (dict, optional): Remaining arguments.

        Returns:
            list: A list of dictionaries containing the categories' details.
        """
        categories = get_categories(categories=categories, colors=colors)

        info_categories = []
        for category_id, category in enumerate(tqdm(categories, desc="Build Categories", leave=True, position=0)):
            info_categories.append({
                "id": category_id,
                "name": str(category.name),
                "color": list(category.color),
                "file_name": str(category.filename),
                "supercategory": str(category.name)
            })
        return info_categories

    @classmethod
    def build_images(cls, images=None, dir_images=None, pattern="*", **kwargs):
        """Build only the images details.
        This method requires images, masks, and colors.

        .. seealso::
            If you want to create precise annotations, 
            use ``make_images`` method.

        Args:
            images (list, optional): List of image paths to be used. Defaults to ``None``.
            dir_images (str, optional): Path to the directory containing images to be used. Defaults to ``None``.
            pattern (str, optional): Pattern used to retrieve images. Defaults to ``"*"``.

        Returns:
            list: A list of dictionaries containing the images' details.
        """
        images_paths = get_paths(files=images, in_dir=dir_images, pattern=pattern)

        info_images = []
        for image_id, image_path in enumerate(tqdm(images_paths, desc="Build Images", leave=True, position=0)):
            image = Image.open(image_path)
            width, height = image.size
            info_images.append({
                "id": image_id,
                "width": width,
                "height": height,
                "file_name": str(image_path)
            })
        return info_images

    @classmethod
    def build(cls, images=None, categories=None, labels=None,
              dir_images=None, dir_labels=None, colors=None,
              pattern_image="*", pattern_label="*", **kwargs):
        """Generate annotations and meta data from images, categories and masks (a.k.a labels).
        This method requires images, masks, and colors. Note that categories are optional,
        as only their name and color are used during the process.
        Therefore to avoid loading expensive data in memory, 
        you can simply specify categories names and colors through the ``colors`` argument.
        Although this method is fast, it is not precise for small scales:
        the objects are not clearly separated in a mask, and some are merged.
        
        .. seealso::
            If you want to create precise annotations, 
            use ``make`` method.

        Args:
            images (list, optional): List of image paths to be used. Defaults to ``None``.
            categories (list, optional): List of loaded categories to be used. Defaults to ``None``.
            labels (list, optional): List of mask paths to be used. Defaults to ``None``.
            dir_images (str, optional): Path to the directory containing images to be used. Defaults to ``None``.
            dir_labels (str, optional): Path to the directory containing masks to be used. Defaults to ``None``.
            colors (dict, optional): Dictionary of ``{name: color}`` associated to the categories. 
                Here ``name`` refers to a category's name and ``color`` its color. Defaults to ``None``.
            pattern (str, optional): Pattern used to retrieve images and masks. Defaults to ``"*"``.

        Returns:
            Annotation: The created annotations.
        """
        images_paths = get_paths(files=images, in_dir=dir_images, pattern=pattern_image)
        labels_paths = get_paths(files=labels, in_dir=dir_labels, pattern=pattern_label)
        categories = get_categories(categories=categories, colors=colors)

        info_images = cls.build_images(images=images_paths, **kwargs)
        info_categories = cls.build_categories(categories=categories, **kwargs)
        info_annotations = cls.build_annotations(images=images_paths, labels=labels_paths, categories=categories, **kwargs)

        return cls(images=info_images, categories=info_categories, annotations=info_annotations)

    @classmethod
    @abstractmethod
    def make_annotations(cls, images=None, categories=None,
                         dir_images=None, dir_categories=None,
                         pattern_image="*", pattern_category="*", **kwargs):
        """Make the annotations details.
        As opposed to ``build``, this method requires the geometries within each category.
        Colors and masks are therefore not required. 
        Therefore, this process is slower than ``build`` one.

        .. seealso::
            For a faster but less precise implementation,
            use ``build_annotations`` method.

        Args:
            images (list, optional): List of image paths to be used. Defaults to ``None``.
            categories (list, optional): List of loaded categories to be used. Defaults to ``None``.
            dir_images (str, optional): Path to the directory containing images to be used. Defaults to ``None``.
            dir_categories (str, optional): Path to the directory containing categories to be used. Defaults to ``None``.
            pattern_image (str, optional): Pattern used to retrieve images. Defaults to ``"*"``.
            pattern_category (str, optional): Pattern used to retrieve categories. Defaults to ``"*"``.

        Returns:
            list: A list of dictionaries containing the annotations' details.
        """
        raise NotImplementedError

    @classmethod
    def make_images(cls, **kwargs):
        """Make the images details.
        As opposed to ``build``, this method requires the geometries within each category.
        Colors and masks are therefore not required. 
        Therefore, this process is slower than ``build`` one.

        .. seealso::
            For a faster but less precise implementation,
            use ``build_images`` method.

        Args:
            kwargs (dict, optional): Arguments used to build images.

        Returns:
            list: A list of dictionaries containing the images' details.
        """
        return cls.build_images(**kwargs)

    @classmethod
    def make_categories(cls, categories=None, dir_categories=None, pattern="*", **kwargs):
        """Make the annotations details.
        As opposed to ``build``, this method requires the geometries within each category.
        Colors and masks are therefore not required. 
        Therefore, this process is slower than ``build`` one.

        .. seealso::
            For a faster but less precise implementation,
            use ``build_categories`` method.

        Args:
            categories (list, optional): List of loaded categories to be used. Defaults to ``None``.
            dir_categories (str, optional): Path to the directory containing categories to be used. Defaults to ``None``.
            pattern (str, optional): Pattern used to retrieve categories. Defaults to ``"*"``.

        Returns:
            list: A list of dictionaries containing the categories' details.
        """
        categories = get_categories(categories=categories, dir_categories=dir_categories, pattern=pattern)

        info_categories = []
        for category_id, category in enumerate(tqdm(categories, desc="Build Categories", leave=True, position=0)):
            info_categories.append({
                "id": category_id,
                "name": str(category.name),
                "supercategory": str(category.name),
                "color": list(category.color),
                "file_name": str(category.filename)
            })
        return info_categories

    @classmethod
    def make(cls, images=None, categories=None,
             dir_images=None, dir_categories=None,
             pattern_image="*", pattern_category="*", **kwargs):
        """Make the annotations and meta data details.
        As opposed to ``build``, this method requires the geometries within each category.
        Colors and masks are therefore not required. 
        Therefore, this process is slower than ``build`` one.

        .. warning::
            The images must be georeferenced, 
            preferably in the same coordinate reference system than the categories.

        .. seealso::
            For a faster but less precise implementation,
            use ``build`` method.

        Args:
            images (list, optional): List of image paths to be used. Defaults to ``None``.
            categories (list, optional): List of loaded categories to be used. Defaults to ``None``.
            dir_images (str, optional): Path to the directory containing images to be used. Defaults to ``None``.
            dir_categories (str, optional): Path to the directory containing categories to be used. Defaults to ``None``.
            pattern_image (str, optional): Pattern used to retrieve images. Defaults to ``"*"``.
            pattern_category (str, optional): Pattern used to retrieve categories. Defaults to ``"*"``.

        Returns:
            Annotation: The created annotations.
        """
        images_paths = get_paths(files=images, in_dir=dir_images, pattern=pattern_image)
        categories = get_categories(categories=categories, dir_categories=dir_categories, pattern=pattern_category)

        info_images = cls.make_images(images=images_paths, **kwargs)
        info_categories = cls.make_categories(categories=categories, **kwargs)
        info_annotations = cls.make_annotations(images=images_paths, categories=categories, **kwargs)

        return cls(images=info_images, categories=info_categories, annotations=info_annotations)

    def to_dict(self, root=None):
        """Convert the annotations and meta data to a dictionary.

        Args:
            root (str, optional): Make the annotations' file relative to a root. Defaults to ``None``.

        Returns:
            dict: The converted annotations.
        """
        root = root or "."
        images = deepcopy(self.images)
        categories = deepcopy(self.categories)
        annotations = deepcopy(self.annotations)

        for image in images:
            image["file_name"] = relative_path(image.get("file_name", None), root)
        for category in categories:
            category["file_name"] = relative_path(category.get("file_name", None), root)
        for annotation in annotations:
            annotation["image_name"] = relative_path(annotation.get("image_name", None), root)

        return {
            "info": self.info,
            "images": images,
            "categories": categories,
            "annotations": annotations
        }

    @abstractmethod
    def save(self, out_file, **kwargs):
        """Save the annotations to the disk.

        Args:
            out_file (str): Name of the output file. 
                To keep both annotations and meta data, it is recommended to save in ``JSON`` format.
        """
        raise NotImplementedError

    def get_image(self, image_id):
        """Get the image from its id.

        Args:
            image_id (int): ID of the image to be retrieved.

        Returns:
            dict: Corresponding image information.
        """
        for image in self.images:
            if image["id"] == image_id:
                return image
        return None

    def get_category(self, category_id):
        """Get a category from its id.

        Args:
            category_id (int): ID of the category.

        Returns:
            dict: Corresponding category.
        """
        for category in self.categories:
            if category["id"] == category_id:
                return deepcopy(category)
        return None

    def get_annotation(self, annotation_id):
        """Get an annotation from its id.

        Args:
            annotation_id (int): ID of the annotation.

        Returns:
            dict: Corresponding annotation.
        """
        for annotation in self.annotations:
            if annotation["id"] == annotation_id:
                return deepcopy(annotation)
        return None

    def get_labels(self, image_id):
        """Get the list of label(s) associated to an image.

        Args:
            image_id (int): ID of the image.

        Returns:
            list: List of dictionary containing the labels.
        """
        labels = []
        for annotation in self.annotations:
            if annotation["image_id"] == image_id:
                labels.append(deepcopy(annotation))
        return labels

    def inner_repr(self):
        return f"images={len(self.images)}, categories={len(self.categories)}, annotations={len(self.annotations)}"

    def __repr__(self):
        return f"{self.__class__.__name__}({self.inner_repr()})"

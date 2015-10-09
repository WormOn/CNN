__author__ = 'Olav'

import numpy as np
from abc import ABCMeta, abstractmethod
import os
import gzip
import theano
import theano.tensor as T
from PIL import Image
import math

class Creator(object):
    '''
    Dynamically load and convert data to appropriate format for theano.
    '''
    def _get_dataset(self, path):
        content = os.listdir(path)
        if not all(x in ['train', 'valid', 'test'] for x in content):
            raise Exception('Folder does not contain image or label folder. Path probably not correct')
        return content

    def _create_xy(self, d, l, start, end):
        '''Return dataset in the form data, label'''
        return d[start:end], l[start:end]

    def create_image_data(self, path):
        image = Image.open(path, 'r')
        arr =  np.asarray(image, dtype=theano.config.floatX) / 255
        arr = np.rollaxis(arr, 2, 0)
        arr = arr.reshape(3, arr.shape[1]* arr.shape[2])

        image.close()
        return arr

    def create_image_label(self, path):
        #TODO: Euclidiean to dist, ramp up to definite roads. Model label noise in labels?
        '''
        Opens greyscale image from path. Converts to numpy with new range (0,1).
        Binary image so all values should be either 0 or 1, but edges might have values in between 0 and 255.
        Convert label matrix to integers and invert the matrix. 1: indicate class being present at that place
        0 : The class not present at pixel location.
        '''
        y_size = 16
        padding = 24
        image = Image.open(path, 'r').convert('L')
        #label = np.array(image.getdata())
        label = np.asarray(image) / 255
        #TODO: Not that general you know

        label = label[padding : padding+y_size, padding : padding+y_size ]
        label = label.reshape(y_size*y_size)

        label = label / 255
        label = np.floor(label)
        label = label.astype(int)
        label = 1 - label
        image.close()
        return label

    def _get_image_files(self, path):
        print("Retrieving", path)
        included_extenstions = ['jpg','png', 'tiff', 'tif'];
        return [fn for fn in os.listdir(path) if any([fn.endswith(ext) for ext in included_extenstions])]

    def _merge_to_examples(self, path):
        '''
        Each path should contain a data and labels folder containing images.
        Creates a list of tuples containing path name for data and label.
        '''
        tiles = self._get_image_files(os.path.join(path, 'data'))
        labels = self._get_image_files(os.path.join(path, 'labels'))

        if len(tiles) == 0 or len(labels) == 0:
            raise Exception('Data or labels folder does not contain any images')

        if len(tiles) != len(labels):
            raise Exception('Not the same number of tiles and labels')

        for i in range(len(tiles)):
            if os.path.splitext(tiles[i])[0] != os.path.splitext(labels[i])[0]:
                raise Exception('tile', tiles[i], 'does not match label', labels[i])
        return list(zip(tiles, labels))


    def _sample_data(self, base, paths, samples_per_images, rotation=False):
        data = []
        label = []
        print("Sampling examples for", base)
        for i in range(len(paths)):
            d, v = paths[i]
            image = self.create_image_data(os.path.join(base, 'data',  d))
            vector = self.create_image_label(os.path.join(base,'labels', v))
            data.append(image)
            label.append(vector)

            if i % 200 == 0:
                print("Tile: ", i, '/', len(paths))

        data = np.array(data)
        label = np.array(label)
        ddim = data.shape
        data = data.reshape(ddim[0], ddim[1]*ddim[2])
        return data, label

    def dynamically_create(self, dataset_path):
        #TODO: Make a small util program that create the dataset structure
        test_path, train_path, valid_path = self._get_dataset(dataset_path)

        base_test = os.path.join(dataset_path, test_path)
        base_train = os.path.join(dataset_path, train_path)
        base_valid = os.path.join(dataset_path, valid_path)

        test_img_paths = self._merge_to_examples(base_test)
        train_img_paths = self._merge_to_examples(base_train)
        valid_img_paths = self._merge_to_examples(base_valid)

        print(len(test_img_paths), '# test img', len(train_img_paths), "# train img", len(valid_img_paths), "# valid img")

        samples_per_image = 10
        train = self._sample_data(base_test, train_img_paths, samples_per_image)
        test = self._sample_data(base_test, test_img_paths, samples_per_image)
        valid = self._sample_data(base_valid, valid_img_paths, samples_per_image)

        return train, valid, test
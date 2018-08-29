
# coding: utf-8

# In[2]:


import sys
import pickle
import copy
from copy import deepcopy

if __name__ == "__main__":
    path_old = sys.argv[1]
    path_new = sys.argv[2]
    outfile = sys.argv[3]
    
    def get_data(path_old, path_new):
        """
        Открывает файлы аннотаций
        """
        with open(path_old, 'br') as f:
            data_old = pickle.load(f)
        with open(path_new, 'br') as f:
            data_new = pickle.load(f)
        return data_old, data_new
    
    def update_categories():
        """
        Собирает категории двух файлов аннотаций в один список
        Работает только если категории в файлах не повторяются
        """
        categories_merged = []
        [categories_merged.append(category) for category in data_old['categories']]

        n = len(data_old['categories'])
        for i in range(len(data_new['categories'])):
            category = deepcopy(data_new['categories'][i])
            category['id'] = n
            categories_merged.append(category)
            n += 1
        return categories_merged
    
    def get_annotations_by_image_id(image_id, data_src):
        """
        Вынимает из списка аннотаций все с заданным image_id. 
        """
        annotations_list = []
        for annotation in data_src['annotations']:
            if annotation['image_id'] == image_id:
                annotations_list.append(annotation)
        return annotations_list
    
    def merge_annotations():
        """
        Объединяет аннотации из двух файлов
        """
        annotations_old = []
        annotations_new = []
        annotations_merged = []

        for i in range(len(data_merged['images'])): 
            annotations_old = get_annotations_by_image_id(i, data_old) 
            annotations_new = get_annotations_by_image_id(i, data_new)

            [annotations_merged.append(ann) for ann in annotations_old]

            if len(annotations_old) > 0:
                ann_id = annotations_old[-1]['id']+1
            else:
                ann_id = 0

            n = len(data_old['categories'])
            for ann in annotations_new:
                ann_new = copy.deepcopy(ann)
                ann_new['category_id'] += n
                ann_new['id'] = ann_id
                annotations_merged.append(ann_new)

        return annotations_merged
    
    data_old, data_new = get_data(path_old, path_new)
    data_merged = {}
    data_merged['info'] = data_old['info']
    data_merged['images'] = data_old['images']
    data_merged['categories'] = update_categories()
    data_merged['annotations'] = merge_annotations()
    
    with open(outfile, 'bw') as f:
        pickle.dump(data_merged, f)


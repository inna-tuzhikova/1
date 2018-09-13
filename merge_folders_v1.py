
# coding: utf-8

# In[ ]:


import os
import copy
import shutil
import pickle
import hashlib
import argparse
import datetime
from PIL import Image
from pathlib import Path
from os.path import join
from copy import deepcopy

parser = argparse.ArgumentParser()
parser.add_argument("path_old")
parser.add_argument("path_new")
parser.add_argument("folder_name")
args = parser.parse_args()

path_old = args.path_old
path_new = args.path_new
folder_name = args.folder_name

# создаем новую папку
out_folder = join(Path(path_old).parent, folder_name)
try:
    os.mkdir(out_folder)
except FileExistsError:
    print('Folder already exists: ', out_folder)

# создаем хеш-индекс картинок в старой папке
# получаем словарь, где ключ -- хеш, значение -- путь к файлу в старой папке
old_images_filenames = sort_filenames(path_old)
old_images_index = {}
old_images_index = {get_hash(image):image for image in old_images_filenames}

# копируем изображения, создаем хеш-индекс новой папки
def copy_files(src, dst):
    file_formats = ['jpeg', 'bmp', 'png']
    files_to_move = [file for file in os.listdir(src) if file.split('.')[-1] not in file_formats]
    for file in files_to_move:
        shutil.copy2(join(src, file), dst)
copy_files(path_old, out_folder)
new_images_filenames = sort_filenames(path_new)
duplicates = {}

for image in new_images_filenames:
    
    # создаем словарь дубликатов, где ключ -- хеш, значение -- [пути к файлам]
    if get_hash(image) in old_images_index.keys():
        duplicates[get_hash(image)] = [old_images_index[get_hash(image)], image]
        
    # переименовываем файлы пред копированием, если нужно
    elif Path(join(out_folder, image.name)).exists():
        time = str(datetime.datetime.now())[:100].split('.')[-1]
        new_name = time+image.name
        shutil.copy2(image, join(out_folder, new_name))
        
    else:
        shutil.copy2(image, out_folder)

# загружаем аннотации        
data_old = get_data(path_old+'/annotations.pickle')
data_new = get_data(path_new+'/annotations.pickle')
data_merged = {}
data_merged['info'] = data_old['info']

# объединяем категории 
m = 0 # счетчик номеров категорий
categories_merged = copy_categories(data_old) + copy_categories(data_new)

# создаем список путей к файлам объединенной папки
# добавляем изображения и аннотации в списки
images_merged_paths = sort_filenames(out_folder)
annotations_merged = []
images_merged = []

i = 0 # счетчик номеров изображений 
for image_path in images_merged_paths:
    
    if get_hash(image_path) not in duplicates.keys() and get_hash(image_path) in old_images_index.keys():
        n = 0 # счетчик номеров аннотаций
        image = get_image_by_filename(image_path.name, data_old)
        new_image = copy.deepcopy(image)
        new_image['id'] = i
        i += 1
        images_merged.append(new_image)
        for category in categories_merged:
            annotations_to_move = append_per_category(image, category, data_old)
            for a in annotations_to_move:
                a['image_id'] = new_image['id']
                annotations_merged.append(a)
                
    elif get_hash(image_path) not in duplicates.keys() and get_hash(image_path) in new_images_index.keys():
        n = 0 # счетчик номеров аннотаций
        image = get_image_by_filename(image_path.name, data_new)
        new_image = copy.deepcopy(image)
        new_image['id'] = i
        i += 1
        images_merged.append(new_image)
        for category in categories_merged:
            annotations_to_move = append_per_category(image, category, data_new)
            for a in annotations_to_move:
                a['image_id'] = new_image['id']
                annotations_merged.append(a)
                
    elif get_hash(image_path) in duplicates.keys():
        n = 0
        image = get_image_by_filename(image_path.name, data_old)
        new_image = copy.deepcopy(image)
        new_image['id'] = i
        i += 1
        images_merged.append(new_image)
        
        old, new = duplicates.get(get_hash(image_path))
        for category in categories_merged:
            old_annotations = append_per_category(get_image_by_filename(old.name, data_old), category, data_old)
            new_annotations = append_per_category(get_image_by_filename(new.name, data_new), category, data_new)
            for a in old_annotations:
                a['image_id'] = new_image['id']
                annotations_merged.append(a)
            for a in new_annotations:
                a['image_id'] = new_image['id']
                annotations_merged.append(a)

# проверяем на дублирующиеся боксы
final_annotations = []
img_length = len(annotations_merged)
for x in range(img_length):
    recheck_img_anns = [ann for ann in annotations_merged if ann['image_id'] == x]
    iou_matrix = make_iou_matrix(recheck_img_anns)
    cleaned_annotations = del_duplicate_boxes(iou_matrix, recheck_img_anns)
    for a in cleaned_annotations:
        final_annotations.append(a)

data_merged['categories'] = categories_merged
data_merged['images'] = images_merged
data_merged['annotations'] = final_annotations

with open(out_folder+'/annotations.pickle', 'bw') as outfile:
    pickle.dump(data_merged, outfile)
    
    
    
def del_duplicate_boxes(iou_matrix, annotations):
    cleaned_annotations = copy.deepcopy(annotations)
    def remove_annotation(_id, annotations):
        for ann in annotations:
            if ann['id'] == _id:
                annotations.remove(ann)
    for i, row in enumerate(iou_matrix, 1):
        for j, iou in enumerate(row):
            if 1 > iou >= 0.6:
                remove_annotation(i+j, cleaned_annotations)
    for _id, a in enumerate(cleaned_annotations):
        a['id'] = _id
    return cleaned_annotations

def make_iou_matrix(image_annotations):
    iou_matrix = []
    l = len(image_annotations)
    for i in range(l):
        mtrx_row = []
        for j in range(i+1, l):
            iou = check_iou(image_annotations[i], image_annotations[j])
            mtrx_row.append(iou)
        iou_matrix.append(mtrx_row)
    return iou_matrix

def check_iou(annotation_old, annotation_new):
    def interval_overlap(interval_a, interval_b):
        x1, x2 = interval_a
        x3, x4 = interval_b
        if x3 < x1:
            if x4 < x1:
                return 0
            else:
                return min(x2, x4) - x1
        else:
            if x2 < x3:
                return 0
            else:
                return min(x2, x4) - x3
    bbox_1 = annotation_old['bbox']
    bbox_2 = annotation_new['bbox']
    intersect_w = _interval_overlap([bbox_1[0][0], bbox_1[1][0]], [bbox_2[0][0], bbox_2[1][0]])
    intersect_h = _interval_overlap([bbox_1[0][1], bbox_1[1][1]], [bbox_2[0][1], bbox_2[1][1]])
    intersect = intersect_w * intersect_h
    w1, h1 = bbox_1[1][0] - bbox_1[0][0], bbox_1[1][1] - bbox_1[0][1]
    w2, h2 = bbox_2[1][0] - bbox_2[0][0], bbox_2[1][1] - bbox_2[0][1]
    union = w1 * h1 + w2 * h2 - intersect
    return float(intersect) / max(float(union), 0.0000001)

def get_hash(path_to_image):
    return hashlib.md5(path_to_image.read_bytes()).hexdigest()

def copy_files(src, dst):
    file_formats = ['jpeg', 'bmp', 'png']
    files_to_move = [file for file in os.listdir(src) if file.split('.')[-1] not in file_formats]
    for file in files_to_move:
        shutil.copy2(join(src, file), dst)
        
def append_per_category(image, category, data):
    category_annotations = []
    global n
    category_id = check_category_number(category['name'], data['categories'])
    if category_id:
        annotations = get_annotations_by_image_id(image['id'], data)
        old_annotations = get_annotations_by_category_id(category_id[0], annotations)
        if old_annotations:
            for annotation in old_annotations:
                a = copy.deepcopy(annotation)
                a['id'] = n
                a['category_id'] = category['id']
                category_annotations.append(a)
                n += 1
    return category_annotations

def get_image_by_filename(filename, data):
    for image in data['images']:
        if image['file_name'] == filename:
            return image
        
def copy_categories(src):
    global m
    categories = []
    def is_double(cat_name, data):
        for dic in data:
            if dic['name'] == cat_name:
                return True
        return False
    for category in src['categories']:
        cat = copy.deepcopy(category)
        if src == data_new:
            if not is_double(cat['name'], data_old['categories']):
                cat['id'] = m
                categories.append(cat)
                m += 1
        else:
            cat['id'] = m
            categories.append(cat)
            m += 1
    return categories
        
def get_data(src):
    with open(src, 'br') as f:
        data = pickle.load(f)
    return data

def sort_filenames(folder_path):
    p = Path(folder_path)
    images_filenames = filter(lambda x: x.name.lower().endswith(('.jpeg', '.jpg', '.png', '.bmp')),
                              p.iterdir())
    return sorted(list(images_filenames)) 

def get_annotations_by_category_id(category_id, data):
    return [ann for ann in data if ann['category_id'] == category_id]

def check_category_number(category_name, data):
    return [category['id'] for category in data if category['name'] == category_name]

def get_annotations_by_image_id(image_id, data):
    return [ann for ann in data['annotations'] if ann['image_id'] == image_id]


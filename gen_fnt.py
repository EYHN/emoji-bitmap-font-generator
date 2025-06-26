# !/usr/bin/env python
# -*- coding: utf-8 -*-
"""
gen_fnt (https://github.com/aillieo/bitmap-font-generator)
Fast and easy way to generate bitmap font with images
Created by Aillieo on 2017-09-06
With Python 3.5
"""

from functools import reduce
from PIL import Image
import os
import re


def format_str(func):
    def wrapper(*args, **kw):
        ret = func(*args, **kw)
        ret = re.sub(r'[\(\)\{\}]', "", ret)
        ret = re.sub(r'\'(?P<name>\w+)\': ', r"\g<name>=", ret)
        ret = re.sub(r', (?P<name>\w+)=', r" \g<name>=", ret)
        # Remove spaces after commas (for padding and spacing values)
        ret = re.sub(r', ', ",", ret)
        ret = ret.replace("'", '"')
        return ret

    return wrapper


class FntConfig:
    def __init__(self):
        self.info = {
            "face": "Noto Color Emoji",
            "size": 16,
            "bold": 0,
            "italic": 0,
            "charset": "",
            "unicode": 1,
            "stretchH": 100,
            "smooth": 1,
            "aa": 1,
            "padding": (0, 0, 0, 0),
            "spacing": (1, 1),
        }

        self.common = {
            "lineHeight": 100,
            "base": 79,
            "scaleW": 1024,
            "scaleH": 1024,
            "pages": 1,
            "packed": 0
        }

        self.pages = {}

    @format_str
    def __str__(self):
        return 'info ' + str(self.info) + '\ncommon ' + str(self.common) + '\n'


class CharDef:
    def __init__(self, id, file):
        self.file = file
        self.param = {
            "id": id,
            "x": 0,
            "y": 0,
            "width": 0,
            "height": 0,
            "xoffset": 0,
            "yoffset": 0,
            "xadvance": 0,
            "page": 0,
            "chnl": 15
        }
        img = Image.open(self.file)
        # Resize image to 100x100 pixels
        img = img.resize((100, 100), Image.Resampling.LANCZOS)
        # Save the resized image for texture generation
        self.resized_img = img
        self.ini_with_texture_size(img.size)

    @format_str
    def __str__(self):
        return 'char ' + str(self.param)

    def ini_with_texture_size(self, size):
        padding = fnt_config.info["padding"]
        self.param["width"], self.param["height"] = size[0] + padding[1] + padding[3], size[1] + padding[0] + padding[2]
        self.param["xadvance"] = size[0]
        self.param["xoffset"] = - padding[1]
        self.param["yoffset"] = - padding[0]

    def set_texture_position(self, position):
        self.param["x"], self.param["y"] = position

    def set_page(self, page_id):
        self.param["page"] = page_id


class CharSet:
    def __init__(self):
        self.chars = []

    def __str__(self):
        ret = 'chars count=' + str(len(self.chars)) + '\n'
        ret += reduce(lambda char1, char2: str(char1) + str(char2) + "\n", self.chars, "")
        return ret

    def add_new_char(self, new_char):
        self.chars.append(new_char)

    def sort_for_texture(self):
        self.chars.sort(key=lambda char: char.param["width"], reverse=True)
        self.chars.sort(key=lambda char: char.param["height"], reverse=True)


class PageDef:
    def __init__(self, page_id, file):
        self.param = {
            "id": page_id,
            "file": file
        }

    @format_str
    def __str__(self):
        return 'page ' + str(self.param)


class TextureMerger:
    def __init__(self, fnt_name):
        self.charset = CharSet()
        self.pages = []
        self.current_page_id = 0
        self.page_name_base = fnt_name

    def get_images(self):
        png_dir = 'png'
        if not os.path.exists(png_dir):
            png_dir = '.'  # fallback to current directory
        files = os.listdir(png_dir)
        print(f"Processing {len(files)} files in {png_dir} directory...")
        valid_count = 0
        for filename in files:
            if '.' not in filename:
                continue
            name, ext = filename.split('.')
            if ext.lower() == 'png':
                full_path = os.path.join(png_dir, filename)
                if len(name) == 1:
                    new_char = CharDef(ord(name), full_path)
                    self.charset.add_new_char(new_char)
                    valid_count += 1
                elif name[0:2] == '__' and name[2:].isdigit():
                    new_char = CharDef(int(name[2:]), full_path)
                    self.charset.add_new_char(new_char)
                    valid_count += 1
                elif name.startswith('emoji_u') and '_' not in name[7:]:
                    # Extract hex code from emoji_u<hexcode> format, ignore all emojis with modifiers
                    hex_part = name[7:]  # Remove 'emoji_u' prefix
                    try:
                        unicode_code = int(hex_part, 16)
                        new_char = CharDef(unicode_code, full_path)
                        self.charset.add_new_char(new_char)
                        valid_count += 1
                    except ValueError:
                        # Skip files with invalid hex codes
                        continue
        print(f"Found {valid_count} valid characters")
        self.charset.sort_for_texture()

    def save_page(self, texture_to_save, actual_height=None):
        out_dir = 'out'
        current_page_id = len(self.pages)
        file_name = self.page_name_base
        file_name += '_'
        file_name += str(current_page_id)
        file_name += '.png'
        full_path = os.path.join(out_dir, file_name)
        try:
            # If actual_height is provided and smaller than texture height, crop the image
            if actual_height and actual_height < texture_to_save.size[1]:
                print(f"Cropping page {current_page_id} from {texture_to_save.size[1]} to {actual_height} pixels height")
                texture_to_save = texture_to_save.crop((0, 0, texture_to_save.size[0], actual_height))
            texture_to_save.save(full_path, 'PNG')
            self.pages.append(PageDef(current_page_id, file_name))
        except IOError:
            print("IOError: save file failed: " + full_path)

    def next_page(self, texture_to_save):
        if texture_to_save:
            self.save_page(texture_to_save)
        texture_w, texture_h = fnt_config.common["scaleW"], fnt_config.common["scaleH"]
        return Image.new('RGBA', (texture_w, texture_h), (0, 0, 0, 0))

    def gen_texture(self):
        self.get_images()
        print(f"Starting texture generation with {len(self.charset.chars)} characters...")
        texture = self.next_page(None)
        padding = fnt_config.info['padding']
        spacing = fnt_config.info['spacing']
        pos_x, pos_y, row_h = 0, 0, 0
        char_count = 0
        max_y_used = 0  # Track the maximum Y position used
        
        for char in self.charset.chars:
            char_count += 1
            if char_count % 100 == 0:
                print(f"Processing character {char_count}/{len(self.charset.chars)}...")
            # Use the pre-resized image instead of loading from file
            img = char.resized_img
            size_with_padding = (padding[1] + img.size[0] + padding[3], padding[0] + img.size[1] + padding[2])
            if row_h == 0:
                row_h = size_with_padding[1]
                if size_with_padding[0] > texture.size[0] or size_with_padding[1] > texture.size[1]:
                    raise ValueError('page has smaller size than a char')
            need_new_row = texture.size[0] - pos_x < size_with_padding[0]
            if need_new_row:
                # Check if we need a new page after moving to next row
                new_pos_y = pos_y + row_h + spacing[1]
                need_new_page = texture.size[1] - new_pos_y < size_with_padding[1]
            else:
                need_new_page = False

            if need_new_page:
                print(f"Creating new page {len(self.pages)}...")
                texture = self.next_page(texture)
                self.current_page_id = len(self.pages)  # Update current_page_id to the new page
                pos_x, pos_y = 0, 0
                row_h = size_with_padding[1]
                max_y_used = 0  # Reset for new page
            elif need_new_row:
                pos_x = 0
                pos_y += row_h + spacing[1]
                row_h = size_with_padding[1]
            
            char.set_texture_position((pos_x, pos_y))
            texture.paste(img, (pos_x + padding[1], pos_y + padding[0]))
            
            # Update max Y position used (position + character height)
            current_y_end = pos_y + size_with_padding[1]
            max_y_used = max(max_y_used, current_y_end)
            
            pos_x += size_with_padding[0] + spacing[0]
            char.set_page(self.current_page_id)
            
        print(f"Saving final page...")
        # Save the final page with cropped height if it's not fully used
        self.save_page(texture, max_y_used)
        print(f"Generated {len(self.pages)} texture pages")

    def pages_to_str(self):
        return reduce(lambda page1, page2: str(page1) + str(page2) + "\n", self.pages, "")


class FntGenerator:
    def __init__(self, fnt_name):
        self.fnt_name = fnt_name
        self.textureMerger = TextureMerger(fnt_name)

    def gen_fnt(self):
        print(f"Generating font: {self.fnt_name}")
        
        # Create and clean output directory
        out_dir = 'out'
        if os.path.exists(out_dir):
            import shutil
            shutil.rmtree(out_dir)
            print(f"Cleared existing output directory: {out_dir}")
        os.makedirs(out_dir)
        print(f"Created output directory: {out_dir}")
        
        self.textureMerger.gen_texture()
        
        # Update the pages count in fnt_config to reflect actual number of pages generated
        fnt_config.common["pages"] = len(self.textureMerger.pages)
        print(f"Updated pages count to {fnt_config.common['pages']}")
        
        fnt_file_name = self.fnt_name + '.fnt'
        full_path = os.path.join(out_dir, fnt_file_name)
        print(f"Writing font file: {full_path}")
        try:
            with open(full_path, 'w', encoding='utf8') as fnt:
                fnt.write(str(fnt_config))
                fnt.write(self.textureMerger.pages_to_str())
                fnt.write(str(self.textureMerger.charset))
            fnt.close()
            print(f"Successfully created {full_path}")
        except IOError as e:
            print("IOError: save file failed: " + full_path + " - " + str(e))


if __name__ == '__main__':
    fnt_config = FntConfig()
    # Use Noto-Color-Emoji as font name prefix
    font_name = "Noto-Color-Emoji"
    fnt_generator = FntGenerator(font_name)
    fnt_generator.gen_fnt()

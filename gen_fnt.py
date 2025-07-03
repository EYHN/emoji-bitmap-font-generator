# !/usr/bin/env python
# -*- coding: utf-8 -*-
"""
gen_fnt (https://github.com/aillieo/bitmap-font-generator)
Fast and easy way to generate bitmap font with images
Created by Aillieo on 2017-09-06
With Python 3.5
Modified to output JSON format
"""

import os
vipsbin = r'C:\Users\EYHN\Downloads\vips-dev-w64-web-8.17.0\vips-dev-8.17\bin'
add_dll_dir = getattr(os, 'add_dll_directory', None)
if callable(add_dll_dir):
    os.environ['PATH'] = os.pathsep.join((vipsbin, os.environ['PATH']))
    add_dll_dir(vipsbin)
else:
    os.environ['PATH'] = os.pathsep.join((vipsbin, os.environ['PATH']))


from functools import reduce
from PIL import Image
import os
import re
import json
import pyvips
from io import BytesIO

PAGE_SIZE = 1024
CHAR_SIZE = 50

RESOURCE_DIR = ["./noto-emoji/png/128", "./noto-emoji/third_party/region-flags/waved-svg"]

def render_svg_to_image(svg_path, size):
    """
    Render SVG file to PIL Image with specified size using pyvips.
    Handles SVG files that contain references to other SVG files.
    """
    try:
        # First, check if the SVG file contains a reference to another SVG file
        with open(svg_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        # Check if the content is just a filename (not actual SVG content)
        if not content.startswith('<') and content.endswith('.svg'):
            # This file contains a reference to another SVG file
            referenced_file = content.strip()
            svg_dir = os.path.dirname(svg_path)
            referenced_path = os.path.join(svg_dir, referenced_file)
            
            if os.path.exists(referenced_path):
                # Use the referenced file instead
                svg_path = referenced_path
            else:
                print(f"Referenced SVG file not found: {referenced_path}")
                return None
        
        # Load SVG with pyvips and specify size
        image = pyvips.Image.new_from_file(svg_path, dpi=72, scale=1.0)
        
        # Calculate scale factor to resize to target size
        width, height = image.width, image.height
        scale_factor = min(size / width, size / height)
        
        # Resize the image
        if scale_factor != 1.0:
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            image = image.resize(scale_factor)
        else:
            new_width, new_height = width, height
        
        # Create a square canvas and center the image
        if new_width != size or new_height != size:
            # Create white background
            background = pyvips.Image.black(size, size, bands=4)
            background = background + [255, 255, 255, 0]  # Transparent background
            
            # Calculate position to center the image
            left = (size - new_width) // 2
            top = (size - new_height) // 2
            
            # Composite the image onto the background
            image = background.composite2(image, 'over', x=left, y=top)
        
        # Convert to PNG bytes
        png_bytes = image.write_to_buffer('.png')
        
        # Create PIL Image from PNG bytes
        img = Image.open(BytesIO(png_bytes))
            
        return img
    except Exception as e:
        print(f"Error rendering SVG {svg_path}: {e}")
        return None


class FntConfig:
    def __init__(self):
        self.info = {
            "face": "Noto Color Emoji",
            "size": CHAR_SIZE
        }

        self.common = {
            "lineHeight": CHAR_SIZE,
            "base": int(CHAR_SIZE * 0.79)
        }

        self.pages = {}

    def to_dict(self):
        # Return dictionary representation for JSON output
        return {
            "info": self.info,
            "common": self.common
        }


class CharDef:
    def __init__(self, codes, file):
        self.file = file
        # Convert single code to list for consistency
        if isinstance(codes, int):
            codes = [codes]
        self.param = {
            "code": codes,
            "x": 0,
            "y": 0,
            "width": 0,
            "height": 0,
            "xoffset": 0,
            "yoffset": 0,
            "xadvance": 0,
            "page": 0,
        }
        
        # Check if file is SVG or PNG
        if file.lower().endswith('.svg'):
            # Render SVG to image
            img = render_svg_to_image(file, CHAR_SIZE)
            if img is None:
                raise ValueError(f"Failed to render SVG: {file}")
        else:
            # Load PNG image
            img = Image.open(self.file)
            # Resize image to CHAR_SIZE x CHAR_SIZE pixels
            img = img.resize((CHAR_SIZE, CHAR_SIZE), Image.Resampling.LANCZOS)
        
        # Save the resized image for texture generation
        self.resized_img = img
        self.ini_with_texture_size(img.size)

    def to_dict(self):
        # Return dictionary representation for JSON output
        return self.param

    def ini_with_texture_size(self, size):
        padding = (0, 0, 0, 0)
        self.param["width"], self.param["height"] = size[0] + padding[1] + padding[3], size[1] + padding[0] + padding[2]
        self.param["xoffset"] = - padding[1]
        self.param["yoffset"] = - padding[0]
        self.param["xadvance"] = size[0]

    def set_texture_position(self, position):
        self.param["x"], self.param["y"] = position

    def set_page(self, page_id):
        self.param["page"] = page_id


class CharSet:
    def __init__(self):
        self.chars = []

    def to_dict(self):
        # Return dictionary representation for JSON output
        return {
            "count": len(self.chars),
            "chars": [char.to_dict() for char in self.chars]
        }

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

    def to_dict(self):
        # Return dictionary representation for JSON output
        return self.param


class TextureMerger:
    def __init__(self, fnt_name):
        self.charset = CharSet()
        self.pages = []
        self.current_page_id = 0
        self.page_name_base = fnt_name

    def get_images(self):
        valid_count = 0
        
        # Process all directories in RESOURCE_DIR
        for resource_dir in RESOURCE_DIR:
            if not os.path.exists(resource_dir):
                print(f"Resource directory not found: {resource_dir}")
                continue
                
            files = os.listdir(resource_dir)
            print(f"Processing {len(files)} files in {resource_dir} directory...")
            
            for filename in files:
                if '.' not in filename:
                    continue
                name, ext = filename.split('.')
                
                # Process files based on their extension, not directory name
                if ext.lower() in ['png', 'svg']:
                    full_path = os.path.join(resource_dir, filename)
                    
                    # Use the same naming logic for both PNG and SVG files
                    try:
                        if len(name) == 1:
                            # Single character files
                            new_char = CharDef(ord(name), full_path)
                            self.charset.add_new_char(new_char)
                            valid_count += 1
                        elif name[0:2] == '__' and name[2:].isdigit():
                            # Files with __<number> format
                            new_char = CharDef(int(name[2:]), full_path)
                            self.charset.add_new_char(new_char)
                            valid_count += 1
                        elif name.startswith('emoji_u'):
                            # Extract hex codes from emoji_u<hexcode1>_<hexcode2>_... format
                            hex_parts = name[7:].split('_')  # Remove 'emoji_u' prefix and split by '_'
                            unicode_codes = []
                            for hex_part in hex_parts:
                                if hex_part:  # Skip empty parts
                                    unicode_codes.append(int(hex_part, 16))
                            if unicode_codes:  # Only process if we have valid codes
                                new_char = CharDef(unicode_codes, full_path)
                                self.charset.add_new_char(new_char)
                                valid_count += 1
                    except ValueError as e:
                        print(f"Skipping file with invalid format {filename}: {e}")
                        continue
                    except Exception as e:
                        print(f"Failed to process {filename}: {e}")
                        continue
        
        print(f"Found {valid_count} valid characters total")
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
        texture_w, texture_h = PAGE_SIZE, PAGE_SIZE
        return Image.new('RGBA', (texture_w, texture_h), (0, 0, 0, 0))

    def gen_texture(self):
        self.get_images()
        print(f"Starting texture generation with {len(self.charset.chars)} characters...")
        texture = self.next_page(None)
        padding = (0, 0, 0, 0)
        spacing = (1, 1)
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

    def get_pages_data(self):
        # Return pages data for JSON output
        return [page.to_dict() for page in self.pages]


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
        
        # Generate JSON output instead of .fnt format
        json_file_name = self.fnt_name + '.json'
        full_path = os.path.join(out_dir, json_file_name)
        print(f"Writing JSON font file: {full_path}")
        
        try:
            # Create the complete JSON structure
            font_data = {
                "info": fnt_config.info,
                "common": fnt_config.common,
                "pages": self.textureMerger.get_pages_data(),
                "chars": self.textureMerger.charset.to_dict()
            }
            
            with open(full_path, 'w', encoding='utf8') as json_file:
                json.dump(font_data, json_file, separators=(',', ':'), ensure_ascii=False)
            print(f"Successfully created {full_path}")
        except IOError as e:
            print("IOError: save file failed: " + full_path + " - " + str(e))


if __name__ == '__main__':
    fnt_config = FntConfig()
    # Use Noto-Color-Emoji as font name prefix
    font_name = "Noto-Color-Emoji"
    fnt_generator = FntGenerator(font_name)
    fnt_generator.gen_fnt()

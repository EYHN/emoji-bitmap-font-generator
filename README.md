## Requirement

Python 3.x
Pillow
pyvips

## Usage

```
python gen_fnt.py
```

## JSON Format

```json
{
    "info": {
        "face": "Noto Color Emoji",
        "size": 50,
    },
    "common": {
        "lineHeight": 50,
        "base": 39
    },
    "pages": [
        {
            "id": 0,
            "file": "Noto-Color-Emoji_0.png"
        },
        {
            "id": 1,
            "file": "Noto-Color-Emoji_1.png"
        },
        ...
    ],
    "chars": {
        "count": 3845,
        "chars": [
            {
                "code": [
                    35
                ],
                "x": 0,
                "y": 0,
                "width": 50,
                "height": 50,
                "xoffset": 0,
                "yoffset": 0,
                "xadvance": 50,
                "page": 0
            },
            {
                "code": [
                    35,
                    8419
                ],
                "x": 51,
                "y": 0,
                "width": 50,
                "height": 50,
                "xoffset": 0,
                "yoffset": 0,
                "xadvance": 50,
                "page": 0
            },
            ...
        ]
    }
}
```

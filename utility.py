import pygame as pg

def load_and_transform_image(filename, width, height):
    img = pg.image.load(filename)
    return pg.transform.smoothscale(img, (width, height))

def load_piece_images(width, height):
    piece_names = ['king', 'queen', 'bishop', 'knight', 'rook', 'pawn']
    piece_images = {}
    for i in range(6):
        for j in range(2):
            color = 'white' if j == 0 else 'black'
            filename = f'{color}_{piece_names[i]}.png'
            img = load_and_transform_image(f'image\{filename}', width, height)
            piece_images[filename] = img
    return piece_images

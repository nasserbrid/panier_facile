#!/usr/bin/env python3
"""
Script pour générer les icônes PWA de PanierFacile
Utilise PIL (Pillow) pour créer des icônes PNG avec un panier stylisé
"""

from PIL import Image, ImageDraw, ImageFont
import os

# Tailles d'icônes requises pour la PWA
SIZES = [72, 96, 128, 144, 152, 192, 384, 512]

# Couleurs (Bootstrap blue)
BG_COLOR = '#0d6efd'
ICON_COLOR = '#ffffff'

def hex_to_rgb(hex_color):
    """Convertir couleur hex en RGB"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def draw_shopping_cart(draw, size):
    """Dessiner une icône de panier de courses"""
    center_x = size // 2
    center_y = size // 2
    icon_size = int(size * 0.5)
    line_width = max(2, size // 40)

    # Couleur blanche pour l'icône
    color = hex_to_rgb(ICON_COLOR)

    # Corps du panier (trapèze)
    cart_top_y = center_y - icon_size // 4
    cart_bottom_y = center_y + icon_size // 4
    cart_left_top = center_x - icon_size // 3
    cart_right_top = center_x + icon_size // 3
    cart_left_bottom = center_x - icon_size // 4
    cart_right_bottom = center_x + icon_size // 4

    # Dessiner le corps du panier
    draw.polygon([
        (cart_left_top, cart_top_y),
        (cart_left_bottom, cart_bottom_y),
        (cart_right_bottom, cart_bottom_y),
        (cart_right_top, cart_top_y)
    ], outline=color, width=line_width)

    # Poignée du panier (arc)
    handle_bbox = [
        center_x - icon_size // 3,
        center_y - icon_size // 2,
        center_x + icon_size // 3,
        center_y - icon_size // 6
    ]
    draw.arc(handle_bbox, start=180, end=0, fill=color, width=line_width)

    # Roues du panier
    wheel_radius = max(2, size // 30)
    wheel_y = cart_bottom_y + wheel_radius + line_width
    wheel_left_x = cart_left_bottom + icon_size // 8
    wheel_right_x = cart_right_bottom - icon_size // 8

    draw.ellipse([
        wheel_left_x - wheel_radius,
        wheel_y - wheel_radius,
        wheel_left_x + wheel_radius,
        wheel_y + wheel_radius
    ], fill=color)

    draw.ellipse([
        wheel_right_x - wheel_radius,
        wheel_y - wheel_radius,
        wheel_right_x + wheel_radius,
        wheel_y + wheel_radius
    ], fill=color)

    # Texte "PF" (PanierFacile) - seulement pour les grandes tailles
    if size >= 192:
        try:
            # Essayer d'utiliser une police système
            font_size = size // 6
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            # Fallback sur la police par défaut
            font = ImageFont.load_default()

        text = "PF"
        # Utiliser textbbox au lieu de textsize (deprecated)
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        text_x = center_x - text_width // 2
        text_y = center_y + icon_size // 6

        draw.text((text_x, text_y), text, fill=color, font=font)

def generate_icon(size, output_dir):
    """Générer une icône de taille donnée"""
    # Créer une image avec fond transparent
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Dessiner un cercle de fond (bleu Bootstrap)
    bg_color = hex_to_rgb(BG_COLOR) + (255,)  # Ajouter alpha
    draw.ellipse([0, 0, size, size], fill=bg_color)

    # Dessiner le panier
    draw_shopping_cart(draw, size)

    # Sauvegarder l'image
    filename = f"icon-{size}x{size}.png"
    filepath = os.path.join(output_dir, filename)
    img.save(filepath, 'PNG')
    print(f"Genere: {filename}")

    return filepath

def main():
    """Fonction principale"""
    # Créer le dossier de sortie si nécessaire
    output_dir = os.path.join('static', 'icons')
    os.makedirs(output_dir, exist_ok=True)

    print("Generation des icones PWA pour PanierFacile...\n")

    # Générer toutes les tailles
    for size in SIZES:
        generate_icon(size, output_dir)

    print(f"\n{len(SIZES)} icones generees dans {output_dir}/")
    print("\nIcones creees:")
    for size in SIZES:
        print(f"  - icon-{size}x{size}.png")

if __name__ == '__main__':
    try:
        main()
    except ImportError:
        print("Erreur: Pillow n'est pas installe.")
        print("Installez-le avec: pip install Pillow")
    except Exception as e:
        print(f"Erreur: {e}")

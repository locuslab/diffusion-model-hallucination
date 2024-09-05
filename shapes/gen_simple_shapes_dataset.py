from PIL import Image, ImageDraw
import PIL
import random
import math
import numpy as np
import os
# Set the image size
image_size = (21, 63)

shapes = ["triangle", "square", "pentagon"]
p = 0.5
overall_figure_meta_data = {}
correct_meta_data = {}
num_images = 8000
num_images_to_generate = 5000
count = 0
save_dir = "../simple-datasets/simple-shapes-new3"
num_images_with_one_shape = 0
num_images_with_two_shapes = 0
num_images_with_three_shapes = 0
num_images_with_triangle = 0
num_images_with_square = 0
num_images_with_pentagon = 0
if not os.path.exists(save_dir):
    print("Creating directory")
    os.mkdir(os.path.join("../simple-datasets", "simple-shapes-new3"))

for idx in range(num_images):
    image_name = f"{idx}.png"
    overall_figure = []
    overall_figure_meta_data[image_name] = []
    for i in shapes:
        # Create an empty black canvas
        image = Image.new('L', image_size, color=0)
        draw = ImageDraw.Draw(image)

        # Define the area of the square (adjust as needed)
        area = 60  # You can change this value
        prob = 0
        # Calculate the side length of the square
        if i=="square":
            # print('square')
            if random.random() <= p:
                prob = 1
                side_length = int((area ** 0.5))
                # Calculate the maximum valid position for the square
                max_x = image_size[0] - side_length*2
                max_y = image_size[1] - side_length*2

                # Choose a random position for the square within the image
                x1 = random.randint(1, max_x)
                y1 = random.randint(1, max_y)
                # print(x1, y1)
                x2 = x1 + side_length
                y2 = y1 + side_length

                # Draw the square at the randomly chosen position
                draw.rectangle([x1, y1, x2, y2], fill=255, outline=255)
                overall_figure_meta_data[image_name].append(["square", x1, y1, side_length])


        elif i=="triangle":
            # print('triangle')
            if random.random() <= p:
                prob = 1
                side_length = int(math.sqrt((4 * area) / (math.sqrt(3))))
                # print(side_length)
                max_x = image_size[0] - side_length
                max_y = image_size[1] - side_length

                # Choose a random position for the triangle within the image
                x1 = random.randint(0, max_x)
                y1 = random.randint(0, max_y)

                # Calculate the coordinates of the triangle's vertices
                x2 = x1 + side_length
                y2 = y1
                x3 = x1 + side_length // 2
                y3 = y1 + int((side_length * math.sqrt(3)) / 2)

                # Draw the regular triangle at the randomly chosen position
                draw.polygon([(x1, y1), (x2, y2), (x3, y3)], fill=255, outline=255)
                overall_figure_meta_data[image_name].append(["triangle", x1, y1, side_length])
            # Display the image
        elif i=="pentagon":
            if random.random() <= p:
                prob = 1
                side = 5
                
                side_length = int(math.sqrt((4 * area)/ (math.sqrt(5*(5+2*math.sqrt(5)))))) #int(math.sqrt((4 * area) / (math.sqrt(5*(5+2*math.sqrt(5)))
                # print("side_length", side_length)
                max_x = image_size[0] - side_length
                max_y = image_size[1] - side_length
                angle_offset = 72  # Offset to calculate the next vertex
                vertices = []
                x1 = random.randint(side_length, max_x)
                y1 = random.randint(side_length, max_y)
                # print(x1,y1)
                for _ in range(5):
                    x = x1 + side_length * math.cos(math.radians(angle_offset))
                    y = y1 - side_length * math.sin(math.radians(angle_offset))
                    vertices.append((x, y))
                    angle_offset += 72
                # Draw the regular pentagon at the specified position
                draw.polygon(vertices, fill=255, outline=255)
                overall_figure_meta_data[image_name].append(["pentagon", x1, y1, side_length])
        

        img = np.array(image)
        white_pixels_square = np.sum(img == 255)
        # print(img.shape)
        # print(f'{i}: {white_pixels_square}')
        # if prob != 0:
        if i=="square" and prob!=0:
            assert white_pixels_square==64
        if i=="triangle" and prob!=0:
            assert abs(white_pixels_square-65)<=2
        if i=="pentagon" and prob!=0:
            assert abs(white_pixels_square-70)<=2

        overall_figure.append(img)
    overall_figure = np.concatenate(overall_figure, axis=1)
    # print(overall_figure.shape)
    if not overall_figure_meta_data[image_name]:
        print("Black image")
    else:
        new_image_array = np.zeros((64, 64), dtype=np.uint8)

        # Copy the original 63x63 image to the center of the new array
        new_image_array[0:63, 0:63] = overall_figure
        new_image_array = PIL.Image.fromarray(new_image_array)
        new_image_array.save(os.path.join(save_dir, f"{count}.png"))
        correct_meta_data[count] = overall_figure_meta_data[image_name]
        count +=1
        shapes_list = overall_figure_meta_data[image_name] 
        num_shapes = len(overall_figure_meta_data[image_name])
        if num_shapes == 1:
            num_images_with_one_shape += 1
        elif num_shapes == 2:
            num_images_with_two_shapes += 1
        elif num_shapes == 3:
            num_images_with_three_shapes += 1
        for shape_info in shapes_list:
            shape_type = shape_info[0]
            if shape_type == "triangle":
                num_images_with_triangle += 1
            elif shape_type == "square":
                num_images_with_square += 1
            elif shape_type == "pentagon":
                num_images_with_pentagon += 1

    if count>=num_images_to_generate:
        break

print("Number of images with 1 shape:", num_images_with_one_shape)
print("Number of images with 2 shapes:", num_images_with_two_shapes)
print("Number of images with 3 shapes:", num_images_with_three_shapes)
print("Number of images with triangle:", num_images_with_triangle)
print("Number of images with square:", num_images_with_square)
print("Number of images with pentagon:", num_images_with_pentagon)
np.savez(os.path.join(save_dir,"meta_data.npz"), correct_meta_data)


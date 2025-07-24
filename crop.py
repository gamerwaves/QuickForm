import json
import re
import base64
import io
from PIL import Image, ImageDraw  # ImageDraw is used for the example

def crop_image_to_base64(pil_image: Image.Image, bbox_json_string: str) -> list[str]:
    """
    Crops a PIL image using bounding boxes from a formatted JSON string
    and returns a list of Base64 encoded strings for the cropped images.

    Args:
        pil_image (PIL.Image.Image): The input image object.
        bbox_json_string (str): A string containing the bounding boxes,
                                potentially wrapped in markdown ```json ... ```.
                                The format inside is [{"box_2d": [x_min, y_min, x_max, y_max]}, ...].

    Returns:
        list[str]: A list where each element is a Base64 encoded string
                   of a cropped image in JPEG format.

    Raises:
        ValueError: If the JSON string is malformed or cannot be parsed.
    """
    # --- 1. Extract the raw JSON from the formatted string ---
    # This regex handles the ```json ... ``` markdown block
    json_match = re.search(r"```json\s*\n(.*?)\n```", bbox_json_string, re.DOTALL)
    
    if json_match:
        clean_json_str = json_match.group(1)
    else:
        # If no markdown block is found, assume the string is raw JSON
        clean_json_str = bbox_json_string

    # --- 2. Parse the JSON string into a Python list ---
    try:
        bounding_boxes = json.loads(clean_json_str)
        if not isinstance(bounding_boxes, list):
            raise TypeError
    except (json.JSONDecodeError, TypeError):
        raise ValueError("Invalid JSON format. Expected a list of objects, e.g., '[{\"box_2d\": ...}]'")

    # --- 3. Process each bounding box and generate Base64 output ---
    base64_outputs = []
    
    for i, item in enumerate(bounding_boxes):
        if 'box_2d' not in item:
            print(f"Warning: Skipping item {i} as it does not contain a 'box_2d' key.")
            continue

        # The bounding box format is [x_min, y_min, x_max, y_max]
        # PIL's crop requires a tuple: (left, upper, right, lower)
        box = tuple(int(coord) for coord in item['box_2d'])

        # Sanity check for box coordinates
        if not (box[0] < box[2] and box[1] < box[3]):
            print(f"Warning: Skipping invalid box {i}: {box}. (x_min must be < x_max and y_min < y_max)")
            continue

        print(f"Processing box {i}: {box}")
        
        # Crop the image using the bounding box
        cropped_image = pil_image.crop(box)

        # Convert the cropped PIL image to a Base64 string
        # Your provided code snippet is used here.
        buffered = io.BytesIO()
        cropped_image.save(buffered, format="JPEG")
        
        # Encode the bytes to a Base64 string
        img_bytes = buffered.getvalue()
        base64_string = base64.b64encode(img_bytes).decode('utf-8')
        
        base64_outputs.append(base64_string)

    return base64_outputs

# --- Example Usage ---
if __name__ == '__main__':
    # 1. Define the input bounding box string in the specified format
    bbox_data_string = """
```json
[
  {"box_2d": [50, 40, 350, 360]},
  {"box_2d": [400, 450, 750, 750]},
  {"box_2d": [375, 50, 700, 400]}
]
```
"""

    # 2. Create a dummy PIL image for demonstration
    # We'll draw rectangles on it to make the crops visually clear
    print("Creating a dummy 800x800 image...")
    main_image = Image.new('RGB', (800, 800), color='lightblue')
    draw = ImageDraw.Draw(main_image)
    
    # Draw colored rectangles corresponding to the bounding boxes
    draw.rectangle([50, 40, 350, 360], fill='red', outline='black', width=3)
    draw.rectangle([400, 450, 750, 750], fill='green', outline='black', width=3)
    draw.rectangle([375, 50, 700, 400], fill='yellow', outline='black', width=3)
    
    # Save the original dummy image to see what it looks like
    main_image.save("demo_original_image.jpg")
    print("Saved original dummy image to 'demo_original_image.jpg'")

    # 3. Call the function with the dummy image and JSON string
    try:
        base64_results = crop_image_to_base64(main_image, bbox_data_string)
        
        print(f"\nSuccessfully generated {len(base64_results)} cropped images in Base64.")

        # 4. (Optional) Decode and save the results to verify they are correct
        for i, b64_str in enumerate(base64_results):
            print(f"  - Crop {i}: {b64_str[:60]}...") # Print first 60 chars
            
            # Decode the base64 string back to bytes
            image_bytes = base64.b64decode(b64_str)
            
            # Create an image file in memory
            image_file = io.BytesIO(image_bytes)
            
            # Open it as a PIL image
            result_image = Image.open(image_file)
            
            # Save it to disk for verification
            output_filename = f"demo_crop_output_{i}.jpg"
            result_image.save(output_filename)
            print(f"    -> Verified and saved to '{output_filename}'")

    except ValueError as e:
        print(f"An error occurred: {e}")
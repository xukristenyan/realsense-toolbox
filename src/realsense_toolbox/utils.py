import cv2


def draw_overlays(image, overlays):
    copied = image.copy()

    for item in overlays:
        if item["type"] == "dot":
            if item["xy"] is not None:
                cv2.circle(copied, (int(item["xy"][0]), int(item["xy"][1])), item.get("radius", 6), item.get("color", (0, 255, 0)), -1)

        if item["type"] == "text":
            cv2.putText(copied, text=item["text"], org=item.get("position", [50, 50]), color=item.get("color", (0, 0, 255)), fontFace=cv2.FONT_HERSHEY_SIMPLEX, fontScale=1, thickness=3)

        if item["type"] == "box":
            pass
    
    return copied
        

def adjust_depth_image(image):
    return cv2.applyColorMap(cv2.convertScaleAbs(image, alpha=0.09), cv2.COLORMAP_JET)


def quit_keypress():
    key = cv2.waitKey(1)
    return key == 27    # ESC
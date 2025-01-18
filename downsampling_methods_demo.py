import cv2

image = cv2.imread("yourImage.jpg")

nearest = cv2.resize(image, (320, 240), interpolation=cv2.INTER_NEAREST)
linear = cv2.resize(image, (320, 240), interpolation=cv2.INTER_LINEAR)
cubic = cv2.resize(image, (320, 240), interpolation=cv2.INTER_CUBIC)
lanczos = cv2.resize(image, (320, 240), interpolation=cv2.INTER_LANCZOS4)
area = cv2.resize(image, (320, 240), interpolation=cv2.INTER_AREA)

cv2.imshow("Nearest (Fast, Low Quality)", nearest)
cv2.imshow("Linear (Good for Small Changes)", linear)
cv2.imshow("Cubic (Smooth, High Quality)", cubic)
cv2.imshow("Lanczos (Best for Downscaling)", lanczos)
cv2.imshow("Area (Best for Downscaling)", area)

cv2.waitKey(0)
cv2.destroyAllWindows()
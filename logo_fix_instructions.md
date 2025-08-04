# Logo Fix Instructions

The issue is that the logo is not appearing in the PDF receipts because jsPDF needs image data synchronously, but we're trying to load the image asynchronously.

## Solution

Replace the logo loading code in both functions (`generateReceipt` and `generatePaymentReceipt`) with this corrected version:

### For generateReceipt function (around line 1122-1132):

Replace this code:
```javascript
// Add logo image with proper async loading
const img = new Image()
img.onload = function() {
  doc.addImage(img, 'JPEG', 15, 8, 12, 12) // Position logo at (15,8) with size 12x12mm
}
img.onerror = function() {
  // Fallback to placeholder if image fails to load
  doc.setFillColor(220, 38, 38)
  doc.circle(20, 15, 4, 'F')
}
img.src = 'gurukulss.jpg'
```

With this code:
```javascript
// Add logo image - using base64 approach
const canvas = document.createElement('canvas')
const ctx = canvas.getContext('2d')
canvas.width = 50
canvas.height = 50

// Create a simple logo placeholder (you can replace this with actual image data)
ctx.fillStyle = '#4CAF50'
ctx.fillRect(0, 0, 50, 50)
ctx.fillStyle = 'white'
ctx.font = '12px Arial'
ctx.textAlign = 'center'
ctx.fillText('GCI', 25, 30)

const imgData = canvas.toDataURL('image/png')
doc.addImage(imgData, 'PNG', 15, 8, 12, 12)
```

### For generatePaymentReceipt function (around line 1215-1225):

Replace the same code block with the same solution.

## Alternative Solution (if you want to use the actual image):

If you want to use the actual `gurukulss.jpg` image, you'll need to:

1. Convert the image to base64 format
2. Replace the canvas code with the base64 string

Example:
```javascript
// Add logo image - using base64 encoded image
const logoBase64 = 'data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQ...' // Your base64 string here
doc.addImage(logoBase64, 'JPEG', 15, 8, 12, 12)
```

## Why this works:

- jsPDF needs image data immediately when `addImage` is called
- The canvas approach creates the image data synchronously
- The base64 approach provides the image data directly
- Both methods avoid the asynchronous loading issue 
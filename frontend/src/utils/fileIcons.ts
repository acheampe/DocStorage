export function getFileIcon(filename: string): string {
  const ext = filename.split('.').pop()?.toLowerCase();
  switch (ext) {
    case 'pdf':
      return 'picture_as_pdf';
    case 'doc':
    case 'docx':
      return 'description';
    case 'ppt':
    case 'pptx':
      return 'slideshow';
    case 'jpg':
    case 'jpeg':
    case 'png':
    case 'gif':
      return 'image';
    default:
      return 'article';
  }
} 
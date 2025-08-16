import { useState, useRef } from 'react';
import { Upload, X, Camera, Trash2 } from 'lucide-react';
import { Button } from '../ui/Button';

interface AvatarUploadProps {
  currentAvatarUrl?: string;
  onUpload: (file: File) => Promise<void>;
  onRemove: () => Promise<void>;
  isUploading?: boolean;
  className?: string;
}

export function AvatarUpload({ 
  currentAvatarUrl, 
  onUpload, 
  onRemove, 
  isUploading = false,
  className = '' 
}: AvatarUploadProps) {
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [imageError, setImageError] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = async (file: File) => {
    // Validate file type
    if (!file.type.startsWith('image/')) {
      alert('Please select an image file');
      return;
    }

    // Validate file size (max 5MB)
    if (file.size > 5 * 1024 * 1024) {
      alert('Image must be less than 5MB');
      return;
    }

    // Create preview
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);

    try {
      await onUpload(file);
      // Clear preview after successful upload
      setPreviewUrl(null);
      URL.revokeObjectURL(url);
    } catch (error) {
      // Keep preview on error for user to try again
      console.error('Upload failed:', error);
    }
  };

  const handleFileInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      handleFileSelect(file);
    }
  };

  const handleDrop = (event: React.DragEvent) => {
    event.preventDefault();
    setIsDragging(false);

    const file = event.dataTransfer.files[0];
    if (file) {
      handleFileSelect(file);
    }
  };

  const handleDragOver = (event: React.DragEvent) => {
    event.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (event: React.DragEvent) => {
    event.preventDefault();
    setIsDragging(false);
  };

  const handleRemove = async () => {
    if (confirm('Are you sure you want to remove your profile picture?')) {
      try {
        await onRemove();
        setPreviewUrl(null);
        setImageError(false);
      } catch (error) {
        console.error('Remove failed:', error);
      }
    }
  };

  const handleBrowseClick = () => {
    fileInputRef.current?.click();
  };

  const displayImageUrl = previewUrl || currentAvatarUrl;
  const hasImage = displayImageUrl && !imageError;

  return (
    <div className={className}>
      <div className="text-sm font-medium text-[hsl(var(--text))] mb-3">
        Profile Picture
      </div>
      
      <div className="flex items-start gap-4">
        {/* Avatar Preview */}
        <div className="relative">
          <div className="w-24 h-24 rounded-full overflow-hidden bg-[hsl(var(--surface))] border-2 border-[hsl(var(--border))] flex items-center justify-center">
            {hasImage ? (
              <img
                src={displayImageUrl}
                alt="Profile preview"
                className="w-full h-full object-cover"
                onError={() => setImageError(true)}
              />
            ) : (
              <Camera className="h-8 w-8 text-[hsl(var(--text))] opacity-40" />
            )}
          </div>
          
          {isUploading && (
            <div className="absolute inset-0 bg-black bg-opacity-50 rounded-full flex items-center justify-center">
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
            </div>
          )}
        </div>

        {/* Upload Controls */}
        <div className="flex-1">
          <div
            className={`
              border-2 border-dashed rounded-lg p-4 transition-colors cursor-pointer
              ${isDragging 
                ? 'border-[hsl(var(--brand))] bg-[hsl(var(--brand))]/5' 
                : 'border-[hsl(var(--border))] hover:border-[hsl(var(--brand))]'
              }
              ${isUploading ? 'opacity-50 cursor-not-allowed' : ''}
            `}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onClick={!isUploading ? handleBrowseClick : undefined}
          >
            <div className="text-center">
              <Upload className="h-6 w-6 text-[hsl(var(--text))] opacity-60 mx-auto mb-2" />
              <div className="text-sm text-[hsl(var(--text))] mb-1">
                Drop an image here or click to browse
              </div>
              <div className="text-xs text-[hsl(var(--text))] opacity-60">
                JPG, PNG, GIF up to 5MB
              </div>
            </div>
          </div>

          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleFileInputChange}
            className="hidden"
            disabled={isUploading}
          />

          <div className="flex gap-2 mt-3">
            <Button
              variant="outline"
              size="sm"
              onClick={handleBrowseClick}
              disabled={isUploading}
            >
              <Upload className="h-4 w-4 mr-2" />
              Upload
            </Button>
            
            {hasImage && (
              <Button
                variant="outline"
                size="sm"
                onClick={handleRemove}
                disabled={isUploading}
                className="text-red-600 hover:text-red-700"
              >
                <Trash2 className="h-4 w-4 mr-2" />
                Remove
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
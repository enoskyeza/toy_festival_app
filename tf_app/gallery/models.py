# gallery/models.py
import os
from io import BytesIO
from PIL import Image
import ffmpeg
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

from imagekit.models import ImageSpecField
from imagekit.processors import ResizeToFill
from django.core.files.base import ContentFile

from core.models import BaseModel

class Media(BaseModel):
    file = models.FileField(upload_to='media/%Y/%m/')
    # On-demand image thumbnails
    thumb_small = ImageSpecField(
        source='file', processors=[ResizeToFill(200, 200)], format='JPEG', options={'quality': 70}
    )
    thumb_medium = ImageSpecField(
        source='file', processors=[ResizeToFill(400, 400)], format='JPEG', options={'quality': 80}
    )
    # Video poster frame
    poster = models.ImageField(upload_to='media/posters/%Y/%m/', blank=True)
    duration = models.FloatField(null=True, blank=True)
    # Generic relation to attach to any model
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField()
    content_obj = GenericForeignKey('content_type', 'object_id')
    caption = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    app_label = models.CharField(
        max_length=50,
        blank=True,
        help_text="Logical grouping of where this media is used: blog, events, website, etc."
    )
    context = models.CharField(
        max_length=100,
        blank=True,
        help_text="Optional context e.g. 'homepage-banner', 'event-photos', 'post-gallery'"
    )
    MEDIA_TYPES = [
        ('primary', 'Primary'),
        ('gallery', 'Gallery'),
        ('embedded', 'Embedded'),
    ]
    media_type = models.CharField(
        max_length=20,
        choices=MEDIA_TYPES,
        default='gallery',
        help_text="Role of this media in the context"
    )


    class Meta:
        verbose_name_plural = "Media"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Extract poster for video synchronously
        if self.is_video() and not self.poster:
            self._extract_video_poster()

    def is_image(self):
        ext = os.path.splitext(self.file.name)[1].lower()
        return ext in ['.jpg', '.jpeg', '.png', '.gif']

    def is_video(self):
        ext = os.path.splitext(self.file.name)[1].lower()
        return ext in ['.mp4', '.mov', '.avi', '.mkv']

    def _extract_video_poster(self):
        input_path = self.file.path
        out, _ = (
            ffmpeg.input(input_path, ss=0)
                  .filter('scale', 400, -1)
                  .output('pipe:', vframes=1, format='image2', vcodec='mjpeg')
                  .run(capture_stdout=True, capture_stderr=True)
        )
        img = Image.open(BytesIO(out))
        buf = BytesIO()
        img.save(buf, format='JPEG')
        filename = f"poster_{os.path.basename(self.file.name)}.jpg"
        self.poster.save(filename, ContentFile(buf.getvalue()), save=False)
        # Extract duration metadata
        info = ffmpeg.probe(input_path)
        self.duration = float(info['format']['duration'])
        super().save()
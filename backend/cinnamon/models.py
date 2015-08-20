from django.db import models
from pygments.lexer import default
from pygments.lexers import get_all_lexers
from pygments.styles import get_all_styles
from pygments.lexers import get_lexer_by_name
from pygments.formatters.html import HtmlFormatter
from pygments import highlight
from django.core.urlresolvers import reverse
from djangotoolbox.fields import ListField, EmbeddedModelField, DictField
from datetime import datetime, timedelta, date


LEXERS = [item for item in get_all_lexers() if item[1]]
LANGUAGE_CHOICES = sorted([(item[1][0], item[0]) for item in LEXERS])
STYLE_CHOICES = sorted((item, item) for item in get_all_styles())
STATUS_CHOICES =  (
        ('A', 'Active'),
        ('D', 'Deleted'),
        ('P', 'Pending'),
        ('R', 'Reject'),
        )
STATE_CHOICES = ((0, 'Suspended'), (1, 'Active'))
CHALLENGE_ACTION_CHOICES = (('ELIMINATING', 'elimination'),
                            ('INCREASING', 'increasing'),
                            ('SUPPLEMENTING', 'supplementing'))
CREATOR_TYPE_CHOICES = (('U', 'USER'),
                        ('S', 'SYSTEM'))
CHALLENGE_RATING_CHOICES = ((1, 1), (2, 2), (3, 3), (4, 4), (5, 5))
MOOD_CHOICES = ((1, 1), (2, 2), (3, 3), (4, 4), (5, 5))
COMPLETION_CHOICES = (('YES', 'YES'),
                      ('MOSTLY YES', 'MOSTLY YES'),
                      ('MOSTLY NO', 'MOSTLY NO'),
                      ('NOPE. FELL OFF THE WAGON TODAY', 'NOPE. FELL OFF THE WAGON TODAY'))

class Snippet(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    title = models.CharField(max_length=100, blank=True, default='')
    code = models.TextField()
    linenos = models.BooleanField(default=False)
    language = models.CharField(choices=LANGUAGE_CHOICES, default='python', max_length=100)
    style = models.CharField(choices=STYLE_CHOICES, default='friendly', max_length=100)
    owner = models.ForeignKey('auth.User', related_name='snippets')
    highlighted = models.TextField()

    def save(self, *args, **kwargs):
        """
        Use the `pygments` library to create a highlighted HTML
        representation of the code snippet.
        """
        lexer = get_lexer_by_name(self.language)
        linenos = self.linenos and 'table' or False
        options = self.title and {'title': self.title} or {}
        formatter = HtmlFormatter(style=self.style, linenos=linenos,
                                  full=True, **options)
        self.highlighted = highlight(self.code, lexer, formatter)
        super(Snippet, self).save(*args, **kwargs)

    class Meta:
        ordering = ('created',)


class IntroQuestion(models.Model):
    body = models.CharField(null=False, max_length=100)
    status = models.CharField(choices=STATUS_CHOICES, default='A', max_length=1)
    class MongoMeta:
        indexes = [
            [('status', 1)],
        ]

class Symptom(models.Model):
    name = models.CharField(null=False, max_length=50)
    description = models.TextField(max_length=255)
    creator_type = models.CharField(choices=CREATOR_TYPE_CHOICES, max_length=1, default='SYSTEM')
    status = models.CharField(choices=STATUS_CHOICES, default='A', max_length=1)
    created_by = models.ForeignKey('auth.User', related_name='symptom')
    created_ts = models.DateTimeField(auto_now_add=True)

    class MongoMeta:
        indexes = [
            [('name', 1)],
            [('creator_type', 1)],
            [('status', 1)],
            [('created_by', -1)],
            [('created_ts', -1)],
        ]


class HunchTip(models.Model):
    body = models.TextField(max_length=510)
    status = models.CharField(choices=STATUS_CHOICES, default='A', max_length=1)


class Hunch(models.Model): #(e.g. dairy, gluten, medication, soy, sugar)
    name = models.CharField(null=False, max_length=50)
    description = models.TextField(max_length=255)
    tip = ListField(EmbeddedModelField('HunchTip')) #dermatologist say it normally takes bla bla
    status = models.CharField(choices=STATUS_CHOICES, default='A', max_length=1)
    article = ListField(EmbeddedModelField('Article'))
    symptom = ListField(EmbeddedModelField('Symptom'))
    creator_type = models.CharField(choices=CREATOR_TYPE_CHOICES, max_length=1, default='SYSTEM')
    created_by = models.ForeignKey('auth.User', related_name='hunch')
    created_ts = models.DateTimeField(auto_now_add=True)

    class MongoMeta:
        indexes = [
            [('name', 1)],
            [('status', 1)],
            [('created_by', -1)],
            [('created_ts', -1)],
            # [('rating', -1), ('admission', 1)],
            # {'fields': [('location', '2d')], 'min': -42, 'max': 42},
        ]


class HealthCondition(models.Model):
    name = models.CharField(null=False, max_length=50)
    description = models.TextField(max_length=255)
    intro_question = ListField(EmbeddedModelField('IntroQuestion')) #(How is your "skin/condition" today?)
    hunch = ListField(EmbeddedModelField('Hunch'))
    status = models.CharField(choices=STATUS_CHOICES, default='A', max_length=1)
    created_by = models.ForeignKey('auth.User', related_name='condition')
    created_ts = models.DateTimeField(auto_now_add=True)

    class MongoMeta:
        indexes = [
            [('name', 1)],
            [('status', 1)],
            [('created_by', -1)],
            [('created_ts', -1)],        ]


class Article(models.Model):
    title = models.CharField(null=False, max_length=255)
    body = models.TextField(null=False, max_length=1024)
    status = models.CharField(choices=STATUS_CHOICES, default='A', max_length=1)
    link = models.URLField()
    ts = models.DateTimeField(default= datetime.now())
    created_by = models.ForeignKey('auth.User', related_name='article')
    created_ts = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-ts"]

    class MongoMeta:
        indexes = [
            [('ts', -1)],
            [('status', -1)],
            [('created_ts', -1)],
        ]

class ChallengeLog(models.Model):
    symptom = ListField(EmbeddedModelField('Symptoms'))
    date = models.DateField(auto_now_add=True)
    rating = models.IntegerField(choices=CHALLENGE_RATING_CHOICES, default=3, max_length=1)
    mood = models.IntegerField(choices=MOOD_CHOICES, max_length=1)
    complete = models.IntegerField(choices=COMPLETION_CHOICES)

    class MongoMeta:
        indexes = [
            [('date', -1)],
            [('rating', -1)],
            [('mood', -1)],
            [('complete', -1)],
            # [('symptom.name', -1)],
        ]

    class Meta:
        ordering = ["-date"]


class Challenge(models.Model):
    action = models.CharField(null=False, choices=CHALLENGE_ACTION_CHOICES, max_length=30)
    hunch = EmbeddedModelField('Hunch')
    log = ListField(EmbeddedModelField('ChallengeLog'))
    state = models.CharField(choices=STATE_CHOICES, default=1, max_length=1)
    status = models.CharField(choices=STATUS_CHOICES, default='A', max_length=1)
    start_date = models.DateField(auto_now_add=True)
    end_date = models.DateField(default=datetime.now()+timedelta(days=7))
    created_by = models.ForeignKey('auth.User', related_name='challenge')
    created_ts = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-start_date"]

    class MongoMeta:
        indexes = [
            # [('hunch.name', -1)],
            [('state', -1)],
            [('status', -1)],
            [('start_date', -1)],
            [('end_date', -1)],
            [('created_by', -1)],
            [('created_ts', -1)],
        ]


class Answer(models.Model):
    body = models.TextField(max_length=1024)
    status = models.CharField(choices=STATUS_CHOICES, default='A', max_length=1)
    up_vote = models.IntegerField(default=0)
    down_vote = models.IntegerField(default=0)
    created_by = models.ForeignKey('auth.User', related_name='answer')
    created_ts = models.DateTimeField(auto_now_add=True)

    def _get_vote_count(self):
        return self.up_vote - self.down_vote

    vote = property(_get_vote_count)

    class Meta:
        ordering = ["-created_ts"]

    class MongoMeta:
        indexes = [
            [('down_vote', -1)],
            [('up_vote', -1)],
            [('status', -1)],
            [('created_by', -1)],
            [('created_ts', -1)],
        ]


class Questions(models.Model):
    title = models.CharField(null=False, max_length=512)
    body = models.TextField(max_length=1024)
    condition = EmbeddedModelField('HealthCondition')
    answer = ListField(EmbeddedModelField('Answer'))
    status = models.CharField(choices=STATUS_CHOICES, default='A', max_length=1)
    created_by = models.ForeignKey('auth.User', related_name='question')
    created_ts = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_ts"]

    class MongoMeta:
        indexes = [
            [('status', -1)],
            [('created_by', -1)],
            [('created_ts', -1)],
        ]


class Statistic(models.Model):
    body = models.TextField(max_length=1024)
    condition = EmbeddedModelField('HealthCondition')
    hunch = EmbeddedModelField('Hunch')
    users = ListField(EmbeddedModelField('auth.User'))
    status = models.CharField(choices=STATUS_CHOICES, default='A', max_length=1)
    created_ts = models.DateTimeField(auto_now_add=True)

    class MongoMeta:
        indexes = [
            [('status', -1)],
            [('created_ts', -1)],
        ]

    class Meta:
        ordering = ["-created_ts"]


# class Post(models.Model):
#     created_at = models.DateTimeField(auto_now_add=True, db_index=True)
#     title = models.CharField(max_length=255)
#     slug = models.SlugField()
#     body = models.TextField()
#     comments = ListField(EmbeddedModelField('Comment'), editable=False)
#
#     def get_absolute_url(self):
#         return reverse('post', kwargs={"slug": self.slug})
#
#     def __unicode__(self):
#         return self.title
#
#     class Meta:
#         ordering = ["-created_at"]
#
#
# class Comment(models.Model):
#     created_at = models.DateTimeField(auto_now_add=True)
#     body = models.TextField(verbose_name="Comment")
#     author = models.CharField(verbose_name="Name", max_length=255)

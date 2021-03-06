from mock import patch

#from django.conf import settings
from django.core.urlresolvers import reverse

from student.models import UserProfile
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase

from fun.tests.utils import skipUnlessLms
#from fun.tests.utils import setMicrositeTestSettings
from newsfeed.tests.factories import ArticleFactory


def set_instance_id_to_42(this):
    this.instance.id = 42


@skipUnlessLms
class TestNews(ModuleStoreTestCase):

    def setUp(self):
        password = super(TestNews, self).setUp()
        self.user.is_superuser = True
        self.user.save()
        UserProfile.objects.create(user=self.user)
        self.client.login(username=self.user.username, password=password)

    @patch("backoffice.forms.ArticleForm.is_valid")
    @patch("backoffice.forms.ArticleForm.save")
    def test_update_news(self, mock_form_save, mock_form_is_valid):
        news = ArticleFactory.create()
        url = reverse("backoffice:news-detail", kwargs={"news_id": news.id})
        mock_form_is_valid.return_value = True
        response = self.client.post(url)

        self.assertEqual(200, response.status_code)

    @patch("backoffice.forms.ArticleForm.is_valid")
    @patch("backoffice.forms.ArticleForm.save", new=set_instance_id_to_42)
    def test_create_valid_news_redirects_to_news_page(self, mock_form_is_valid):
        url = reverse("backoffice:news-create")
        mock_form_is_valid.return_value = True
        response = self.client.post(url)

        self.assertEqual(302, response.status_code)
        self.assertTrue(response['Location'].endswith(reverse('backoffice:news-detail', kwargs={'news_id': 42})))

    # It seem that setMicrositeTestSettings is invoked even when CMS tests are running but
    # CMS tests settings do not have FAKE_MICROSITE dict which makes skipUnlessLms to be ignored...
    #@setMicrositeTestSettings()
    #def test_get_microsite_news_from_different_microsite(self):
    #    self.user.usersignupsource_set.create(site=settings.FAKE_MICROSITE['SITE_NAME'])
    #    self.user.save()
    #    news = ArticleFactory.create()
    #    news.microsite = "The Dark Side Of The Moon"
    #    news.save()
    #    url = reverse("backoffice:news-detail", kwargs={"news_id": news.id})
    #    response = self.client.get(url)
    #    self.assertEqual(404, response.status_code)

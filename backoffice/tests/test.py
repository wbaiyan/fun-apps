# -*- coding: utf-8 -*-

from django.contrib.auth.models import Group
from django.core.urlresolvers import reverse
from django.test.utils import override_settings
from django.utils.translation import ugettext as _

from lang_pref import LANGUAGE_KEY
from opaque_keys.edx.keys import CourseKey
from openedx.core.djangoapps.user_api.models import UserPreference
from student.tests.factories import UserFactory
from xmodule.modulestore.django import modulestore
from xmodule.modulestore.tests.factories import CourseFactory
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase, TEST_DATA_DIR
from xmodule.modulestore.tests.django_utils import TEST_DATA_MOCK_MODULESTORE

from universities.factories import UniversityFactory

from ..models import Course, Teacher

class BaseBackoffice(ModuleStoreTestCase):
    def setUp(self):
        super(BaseBackoffice, self).setUp()
        self.university = UniversityFactory(name='FUN', code='FUN')
        self.backoffice_group = Group.objects.create(name='fun_backoffice')  # create the group
        self.course = CourseFactory(org=self.university.code, number='001', display_name='test')  # create a non published course
        self.user = UserFactory(username='auth')
        self.list_url = reverse('backoffice-courses-list')


@override_settings(MODULESTORE=TEST_DATA_MOCK_MODULESTORE)
class TestAuthetification(BaseBackoffice):
    def test_auth_not_belonging_to_group(self):
        # Users not belonging to `fun_backoffice` should not log in.
        self.client.login(username=self.user.username, password='test')
        response = self.client.get(self.list_url)
        self.assertEqual(302, response.status_code)

    def test_auth_not_staff(self):
        self.user.groups.add(self.backoffice_group)
        self.client.login(username=self.user.username, password='test')
        response = self.client.get(self.list_url)
        self.assertEqual(200, response.status_code)
        self.assertEqual(0, len(response.context['courses']))  # user is not staff he can not see not published course

    def test_auth_staff(self):
        self.user.groups.add(self.backoffice_group)
        self.user.is_staff = True
        self.user.save()
        self.client.login(username=self.user.username, password='test')
        response = self.client.get(self.list_url)
        self.assertEqual(1, len(response.context['courses']))  # OK


@override_settings(MODULESTORE=TEST_DATA_MOCK_MODULESTORE)
class TestGenerateCertificate(BaseBackoffice):
    def setUp(self):
        super(TestGenerateCertificate, self).setUp()
        self.user.groups.add(self.backoffice_group)
        self.user.is_staff = True
        self.user.save()
        self.client.login(username=self.user.username, password='test')

    def test_certificate(self):
        url = reverse('generate-test-certificate', args=[self.course.id.to_deprecated_string()])
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)
        data = {
            'full_name' : u'super élève',
        }
        response = self.client.post(url, data)
        self.assertEqual('application/pdf', response._headers['content-type'][1])


class BaseCourseDetail(ModuleStoreTestCase):
    def setUp(self):
        super(BaseCourseDetail, self).setUp()
        self.course = CourseFactory(org='fun', number='001', display_name='test')
        self.user = UserFactory(username='delete', is_superuser=True)
        UserPreference.set_preference(self.user, LANGUAGE_KEY, 'en-en')
        self.client.login(username=self.user.username, password='test')
        self.url = reverse('backoffice-course-detail', args=[self.course.id.to_deprecated_string()])


@override_settings(MODULESTORE=TEST_DATA_MOCK_MODULESTORE)
class TestDeleteCourse(BaseCourseDetail):
    def test_get_view(self):
        response = self.client.get(self.url)
        self.assertEqual(200, response.status_code)

    def test_funcourse_automatique_creation(self):
        """A fun Course object should be automaticaly created if it do not already exists."""
        response = self.client.get(self.url)
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, Course.objects.filter(key=self.course.id.to_deprecated_string()).count())

    def test_delete_course(self):
        data = {'action': 'delete-course'}
        response = self.client.post(self.url, data, follow=True)
        self.assertEqual(None, modulestore().get_course(self.course.id))
        self.assertEqual(0, Course.objects.filter(key=self.course.id.to_deprecated_string()).count())
        self.assertIn(_(u"Course <strong>%s</strong> has been deleted.") % self.course.id,
                response.content.decode('utf-8'))

    def test_no_university(self):
        """In a course is not bound to an university, a alert should be shown."""
        response = self.client.get(self.url)
        self.assertIn(_(u"University with code <strong>%s</strong> does not exist.") % self.course.id.org,
                response.content.decode('utf-8'))


@override_settings(MODULESTORE=TEST_DATA_MOCK_MODULESTORE)
class TestAddTeachers(BaseCourseDetail):
    def test_add(self):
        response = self.client.get(self.url)  # call view to create the related fun course
        self.assertEqual(200, response.status_code)

        data = {
            'action': 'update-teachers',
            'teachers-TOTAL_FORMS': '2',
            'teachers-INITIAL_FORMS': '0',
            'teachers-MAX_NUM_FORMS': '5',
            'teachers-0-id': '',
            'teachers-0-order': 0,
            'teachers-0-full_name': "Mabuse",
            'teachers-0-title': "Doctor",
            'teachers-0-DELETE': False,
            'teachers-1-id': '',
            'teachers-1-order': 0,
            'teachers-1-DELETE': False,
            'teachers-1-full_name': "Who",
            'teachers-1-title': "Doctor",
            }
        response = self.client.post(self.url, data)
        self.assertEqual(302, response.status_code)
        funcourse = Course.objects.get(key=self.course.id.to_deprecated_string())
        self.assertEqual(2, funcourse.teachers.count())


@override_settings(MODULESTORE=TEST_DATA_MOCK_MODULESTORE)
class TestDeleteTeachers(BaseCourseDetail):
    def test_delete(self):
        funcourse = Course.objects.create(key=self.course.id.to_deprecated_string())
        t1 = Teacher.objects.create(course=funcourse, full_name="Mabuse", title="Doctor")
        t2 = Teacher.objects.create(course=funcourse, full_name="Who", title="Doctor")
        self.assertEqual(2, funcourse.teachers.count())

        response = self.client.get(self.url)
        self.assertEqual(200, response.status_code)
        self.assertIn("Mabuse", response.content)
        data = {
            'action': 'update-teachers',
            'teachers-TOTAL_FORMS': '2',
            'teachers-INITIAL_FORMS': '2',
            'teachers-MAX_NUM_FORMS': '5',
            'teachers-0-id': t1.id,
            'teachers-0-order': 0,
            'teachers-0-full_name': "Mabuse",
            'teachers-0-title': "Doctor",
            'teachers-0-DELETE': True,
            'teachers-1-id': t2.id,
            'teachers-1-order': 0,
            'teachers-1-DELETE': False,
            'teachers-1-full_name': "Who",
            'teachers-1-title': "Doctor",
            }

        response = self.client.post(self.url, data)
        self.assertEqual(302, response.status_code)
        self.assertEqual(1, funcourse.teachers.count())

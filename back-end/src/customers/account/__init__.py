import collections.abc
import functools
import inspect


class CustomerReloadUps:
    """
    Registers classes for each of the different customer/account
    view functions
    Allows the class to be accessed through custoer_reload_ups.get_class(cls_name)
    The class can then be called by class().get_context_data()
    """

    @classmethod
    def _get_class(cls, class_name):
        return cls.get_classes().get(class_name, None)

    @classmethod
    @functools.lru_cache(maxsize=None)
    def get_classes(cls):
        class_ups = [parent.__dict__.get("class_ups", {}) for parent in inspect.getmro(cls)]
        res = cls.merge_dicts(class_ups)
        return res

    def get_class(self, class_name):
        found = self._get_class(class_name)
        return found

    @staticmethod
    def merge_dicts(dicts):
        """
        Merge dicts in reverse to preference the order of the original list. e.g.,
        merge_dicts([a, b]) will preference the keys in 'a' over those in 'b'.
        """
        merged = {}
        for d in reversed(dicts):
            merged.update(d)
        return merged

    @classmethod
    def register_class(cls, classup, class_name=None):
        if class_name is None:
            class_name = classup.class_name

        if "class_ups" not in cls.__dict__:
            cls.class_ups = {}

        cls.class_ups[class_name] = classup
        return classup


class BaseCustomerReload:
    def get_context_data(self, request):
        pass


class Page(collections.abc.Sequence):
    def __init__(self, number, per_page, num_pages):
        self.number = number
        self.num_pages = num_pages
        self.per_page = per_page

    def __len__(self):
        return len(self.per_page)

    def __getitem__(self, index):
        pass

    def __repr__(self):
        return "<Page %s of %s>" % (self.number, self.num_pages)

    def has_next(self):
        return self.number < self.num_pages

    def has_previous(self):
        return self.number > 1

    def has_other_pages(self):
        return self.has_previous() or self.has_next()

    def next_page_number(self):
        return self.number + 1

    def previous_page_number(self):
        return self.number - 1


customer_reload_ups = CustomerReloadUps()

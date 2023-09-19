import functools
import inspect


class Inject:
    @classmethod
    def _get_cls(cls, cls_name):
        return cls.get_clss().get(cls_name, None)

    @classmethod
    @functools.lru_cache(maxsize=None)
    def get_clss(cls):
        class_ups = [parent.__dict__.get("class_ups", {}) for parent in inspect.getmro(cls)]
        return cls.merge_dicts(class_ups)

    def get_cls(self, cls_name):
        found = self._get_cls(cls_name)
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
    def register_cls(cls, cls_up, cls_name=None):
        if cls_name is None:
            cls_name = cls_up.cls_name

        if "class_ups" not in cls.__dict__:
            cls.class_ups = {}

        cls.class_ups[cls_name] = cls_up
        return cls_up

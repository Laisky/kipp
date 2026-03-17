#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations

import threading
from unittest import TestCase

from kipp.libs import singleton, SingletonMixin, PY2, PY3
from kipp.libs.exceptions import KippException, KippAIOException, KippAIOTimeoutError
from kipp.libs.aio import MultiEvent, Queue, Event


class SingletonDecoratorTestCase(TestCase):
    """Tests for the singleton decorator."""

    def test_returns_same_instance(self):
        @singleton
        class MyClass:
            def __init__(self):
                self.value = 42

        a = MyClass()
        b = MyClass()
        self.assertIs(a, b)
        self.assertEqual(a.value, 42)

    def test_different_classes_get_different_singletons(self):
        @singleton
        class ClassA:
            pass

        @singleton
        class ClassB:
            pass

        a = ClassA()
        b = ClassB()
        self.assertIsNot(a, b)

    def test_singleton_preserves_init_state(self):
        @singleton
        class Counter:
            def __init__(self):
                self.count = 0

        c1 = Counter()
        c1.count = 5
        c2 = Counter()
        self.assertEqual(c2.count, 5)

    def test_singleton_no_args_call(self):
        @singleton
        class Simple:
            pass

        instance = Simple()
        self.assertIsNotNone(instance)

    def test_singleton_wraps_preserves_name(self):
        @singleton
        class NamedClass:
            pass

        self.assertEqual(NamedClass.__wrapped__.__name__, "NamedClass")

    def test_singleton_with_init_args_captured_at_decoration(self):
        """Args and kwargs passed to @singleton are forwarded to __init__
        at first instantiation, not at call time."""

        class Configurable:
            def __init__(self, x, y=10):
                self.x = x
                self.y = y

        wrapped = singleton(Configurable, 5, y=20)
        obj1 = wrapped()
        obj2 = wrapped()
        self.assertIs(obj1, obj2)
        self.assertEqual(obj1.x, 5)
        self.assertEqual(obj1.y, 20)

    def test_singleton_multiple_calls_never_reinitialize(self):
        call_count = 0

        @singleton
        class Tracked:
            def __init__(self):
                nonlocal call_count
                call_count += 1

        Tracked()
        Tracked()
        Tracked()
        self.assertEqual(call_count, 1)


class SingletonMixinTestCase(TestCase):
    """Tests for SingletonMixin."""

    def test_returns_same_instance(self):
        class MyService(SingletonMixin):
            def __init__(self):
                self.data = "initial"

        a = MyService()
        b = MyService()
        self.assertIs(a, b)

    def test_subclasses_are_independent(self):
        class ServiceA(SingletonMixin):
            pass

        class ServiceB(SingletonMixin):
            pass

        a = ServiceA()
        b = ServiceB()
        self.assertIsNot(a, b)
        self.assertIsInstance(a, ServiceA)
        self.assertIsInstance(b, ServiceB)

    def test_isinstance_check(self):
        class MyMixin(SingletonMixin):
            pass

        obj = MyMixin()
        self.assertIsInstance(obj, MyMixin)
        self.assertIsInstance(obj, SingletonMixin)

    def test_subclass_inherits_parent_instance(self):
        """Each concrete subclass should maintain its own singleton instance."""

        class Parent(SingletonMixin):
            pass

        class Child(Parent):
            pass

        p = Parent()
        c = Child()
        self.assertIsNot(p, c)
        self.assertIsInstance(c, Parent)
        self.assertIsInstance(c, Child)

    def test_thread_safety(self):
        class ThreadSafeService(SingletonMixin):
            def __init__(self):
                self.value = 0

        instances = []
        errors = []

        def create_instance():
            try:
                inst = ThreadSafeService()
                instances.append(inst)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=create_instance) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0)
        self.assertTrue(len(instances) > 0)
        first = instances[0]
        for inst in instances[1:]:
            self.assertIs(inst, first)

    def test_same_new_but_init_reruns(self):
        """SingletonMixin reuses __new__ but Python still calls __init__
        on the returned object, so __init__ resets state each time."""

        class SharedState(SingletonMixin):
            def __init__(self):
                self.items = []

        a = SharedState()
        a.items.append("hello")
        b = SharedState()
        self.assertIs(a, b)
        self.assertEqual(b.items, [])

    def test_mutation_without_init_reset(self):
        class NoInit(SingletonMixin):
            pass

        a = NoInit()
        a.data = "persistent"
        b = NoInit()
        self.assertEqual(b.data, "persistent")

    def test_mixin_with_args_to_init(self):
        class WithArgs(SingletonMixin):
            def __init__(self, x=0):
                self.x = x

        a = WithArgs(10)
        b = WithArgs(20)
        self.assertIs(a, b)
        # __init__ re-runs with new args on existing instance
        self.assertEqual(b.x, 20)


class ExceptionHierarchyTestCase(TestCase):
    """Tests for KippException -> KippAIOException -> KippAIOTimeoutError."""

    def test_kipp_exception_is_base_exception(self):
        self.assertTrue(issubclass(KippException, Exception))

    def test_kipp_aio_exception_inherits_kipp_exception(self):
        self.assertTrue(issubclass(KippAIOException, KippException))

    def test_kipp_aio_timeout_inherits_kipp_aio_exception(self):
        self.assertTrue(issubclass(KippAIOTimeoutError, KippAIOException))

    def test_kipp_aio_timeout_inherits_kipp_exception(self):
        self.assertTrue(issubclass(KippAIOTimeoutError, KippException))

    def test_catch_kipp_exception_catches_timeout(self):
        with self.assertRaises(KippException):
            raise KippAIOTimeoutError("timed out")

    def test_catch_kipp_aio_catches_timeout(self):
        with self.assertRaises(KippAIOException):
            raise KippAIOTimeoutError("timed out")

    def test_exception_message_preserved(self):
        err = KippAIOTimeoutError("custom message")
        self.assertEqual(str(err), "custom message")

    def test_kipp_exception_not_subclass_of_aio(self):
        self.assertFalse(issubclass(KippException, KippAIOException))

    def test_isinstance_checks(self):
        err = KippAIOTimeoutError()
        self.assertIsInstance(err, KippAIOTimeoutError)
        self.assertIsInstance(err, KippAIOException)
        self.assertIsInstance(err, KippException)
        self.assertIsInstance(err, Exception)


class MultiEventTestCase(TestCase):
    """Tests for MultiEvent barrier-style event."""

    def test_fires_after_n_sets(self):
        evt = MultiEvent(3)
        self.assertFalse(evt.is_set())
        evt.set()
        self.assertFalse(evt.is_set())
        evt.set()
        self.assertFalse(evt.is_set())
        evt.set()
        self.assertTrue(evt.is_set())

    def test_single_worker(self):
        evt = MultiEvent(1)
        self.assertFalse(evt.is_set())
        evt.set()
        self.assertTrue(evt.is_set())

    def test_invalid_n_workers_zero_raises_kipp_aio_exception(self):
        with self.assertRaises(KippAIOException):
            MultiEvent(0)

    def test_invalid_n_workers_negative_raises_kipp_aio_exception(self):
        with self.assertRaises(KippAIOException):
            MultiEvent(-1)

    def test_invalid_n_workers_string_raises_kipp_aio_exception(self):
        with self.assertRaises(KippAIOException):
            MultiEvent("3")

    def test_invalid_n_workers_float_raises_kipp_aio_exception(self):
        with self.assertRaises(KippAIOException):
            MultiEvent(2.5)

    def test_invalid_n_workers_none_raises_kipp_aio_exception(self):
        with self.assertRaises(KippAIOException):
            MultiEvent(None)

    def test_thread_safe_set(self):
        n = 50
        evt = MultiEvent(n)

        def do_set():
            evt.set()

        threads = [threading.Thread(target=do_set) for _ in range(n)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertTrue(evt.is_set())

    def test_extra_sets_after_fired_do_not_error(self):
        evt = MultiEvent(1)
        evt.set()
        self.assertTrue(evt.is_set())
        # Extra set calls should not raise
        evt.set()
        self.assertTrue(evt.is_set())

    def test_is_subclass_of_event(self):
        self.assertTrue(issubclass(MultiEvent, Event))


class QueueTestCase(TestCase):
    """Tests for Queue.empty()."""

    def test_empty_when_new(self):
        q = Queue()
        self.assertTrue(q.empty())

    def test_not_empty_after_put(self):
        q = Queue()
        q.put_nowait("item")
        self.assertFalse(q.empty())

    def test_empty_after_put_and_get(self):
        q = Queue()
        q.put_nowait("item")
        q.get_nowait()
        self.assertTrue(q.empty())

    def test_multiple_items(self):
        q = Queue()
        q.put_nowait("a")
        q.put_nowait("b")
        self.assertFalse(q.empty())
        q.get_nowait()
        self.assertFalse(q.empty())
        q.get_nowait()
        self.assertTrue(q.empty())

    def test_qsize_matches_empty(self):
        q = Queue()
        self.assertEqual(q.qsize(), 0)
        self.assertTrue(q.empty())
        q.put_nowait(1)
        self.assertEqual(q.qsize(), 1)
        self.assertFalse(q.empty())


class PythonVersionTestCase(TestCase):
    """Tests for PY2/PY3 version flags."""

    def test_py3_is_true(self):
        self.assertTrue(PY3)

    def test_py2_is_false(self):
        self.assertFalse(PY2)

    def test_py2_and_py3_mutually_exclusive(self):
        self.assertNotEqual(PY2, PY3)

    def test_types_are_bool(self):
        self.assertIsInstance(PY2, bool)
        self.assertIsInstance(PY3, bool)

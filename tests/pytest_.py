from invoke import MockContext
from mock import Mock

from invocations.pytest import test


class test_:
    def setup(self):
        self.c = MockContext()
        # TODO: cloned from a tiny part of some harness stuff for
        # packaging.release; probably wants moving to somewhere more central if
        # not some kinda invoke-test lib?
        object.__setattr__(self.c, "run", Mock())
        self.defaultstr = "--verbose --color=yes --capture=sys"

    def _expect_flags(self, flagstr):
        expected = "pytest {}".format(self.defaultstr)
        if flagstr:
            expected = expected + " " + flagstr
        self.c.run.assert_called_once_with(expected, pty=True)

    def defaults_to_verbose_color_and_syscapture_with_pty_True(self):
        test(self.c)
        self._expect_flags("")

    def can_turn_off_or_change_defaults(self):
        test(self.c, verbose=False, color=False, pty=False, capture="no")
        self.c.run.assert_called_once_with("pytest --capture=no", pty=False)

    def can_disable_warnings(self):
        test(self.c, warnings=False)
        self._expect_flags("--disable-warnings")

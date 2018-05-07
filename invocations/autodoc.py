"""
Sphinx autodoc hooks for documenting Invoke-level objects such as tasks.

Unlike most of the rest of Invocations, this module isn't for reuse in the
"import and call functions" sense, but instead acts as a Sphinx extension which
allows Sphinx's `autodoc`_ functionality to see and document
Invoke tasks and similar Invoke objects.

.. note::
    This functionality is mostly useful for redistributable/reusable tasks
    which have been defined as importable members of some Python package or
    module, as opposed to "local-only" tasks that live in a single project's
    ``tasks.py``.

    However, it will work for any tasks that Sphinx autodoc can import, so in a
    pinch you could for example tweak ``sys.path`` in your Sphinx ``conf.py``
    to get it loading up a "local" tasks file for import.

To use:

- Add ``"sphinx.ext.autodoc"`` and ``"invocations.autodoc"`` to your Sphinx
  ``conf.py``'s ``extensions`` list.
- Use Sphinx autodoc's ``automodule`` directive normally, aiming it at your
  tasks module(s), e.g. ``.. automodule:: myproject.tasks`` in some ``.rst``
  document of your choosing.

    - As noted above, this only works for modules that are importable, like any
      other Sphinx autodoc use case.
    - Unless you want to opt-in which module members get documented, use
      ``:members:`` or add ``"members"`` to your ``conf.py``'s
      ``autodoc_default_flags``.
    - By default, only tasks with docstrings will be picked up, unless you also
      give the ``:undoc-members:`` flag or add ``:undoc-members:`` / add
      ``"undoc-members"`` to ``autodoc_default_flags``.
    - Please see the `autodoc`_ docs for details on these settings and more!

- Build your docs, and you should see your tasks showing up as documented
  functions in the result.


.. _autodoc: http://www.sphinx-doc.org/en/master/ext/autodoc.html
"""

from sphinx.ext.autodoc import FunctionDocumenter


class TaskDocumenter(FunctionDocumenter):
    objtype = 'task'


def setup(app):
    app.add_autodocumenter(TaskDocumenter)

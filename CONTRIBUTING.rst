============================
Submitting Patches to sesdev
============================

If you have a patch that fixes an issue, feel free to open a GitHub pull request
("PR") targeting the "master" branch, but do read this document first, as it
contains important information for ensuring that your PR passes code review
smoothly.

Sign your work
--------------

The sign-off is a simple line at the end of the explanation for the
commit, which certifies that you wrote it or otherwise have the right to
pass it on as a open-source patch. The rules are pretty simple: if you
can certify the below:

Developer's Certificate of Origin 1.1
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

By making a contribution to this project, I certify that:

   (a) The contribution was created in whole or in part by me and I
       have the right to submit it under the open source license
       indicated in the file; or

   (b) The contribution is based upon previous work that, to the best
       of my knowledge, is covered under an appropriate open source
       license and I have the right under that license to submit that
       work with modifications, whether created in whole or in part
       by me, under the same open source license (unless I am
       permitted to submit under a different license), as indicated
       in the file; or

   (c) The contribution was provided directly to me by some other
       person who certified (a), (b) or (c) and I have not modified
       it.

   (d) I understand and agree that this project and the contribution
       are public and that a record of the contribution (including all
       personal information I submit with it, including my sign-off) is
       maintained indefinitely and may be redistributed consistent with
       this project or the open source license(s) involved.

then you just add a line saying ::

        Signed-off-by: Random J Developer <random@developer.example.org>

using your real name (sorry, no pseudonyms or anonymous contributions.)

Git can sign off on your behalf
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Please note that git makes it trivially easy to sign commits. First, set the
following config options::

    $ git config --list | grep user
    user.email=my_real_email_address@example.com
    user.name=My Real Name

Then just remember to use ``git commit -s``. Git will add the ``Signed-off-by``
line automatically.

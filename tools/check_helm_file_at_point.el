;;; check_helm_file_at_point.el --- ERT tests: C-x C-f resolves repo-root-relative names  -*- lexical-binding: t -*-
;;
;; Checks that a config's helm.el makes helm-find-files' "file at point" prefill
;; resolve a repo-root-relative name (tasks/reference/x.md written inside
;; tasks/foo.md), via (setq helm-ff-guess-ffap-filenames t): Emacs's own ffap
;; guesser, which also looks in parent folders.
;;
;; Run headless (see check_helm_file_at_point.sh):
;;   emacs --batch -Q --eval '(setq bill/test-elpa "<elpa dir>" bill/test-subject "<the .el under test>")' \
;;         -l check_helm_file_at_point.el -f ert-run-tests-batch-and-exit
;;
;; Builds a throwaway git repo:
;;   tasks/foo.md                 mentions the names below
;;   tasks/reference/x.md         target of the root-relative name
;;   tasks/reference/local.md     file-relative from tasks/ ...
;;   reference/local.md           ... and ALSO present from the root (file-relative must win)
;;   tasks/archive/2026/11/07/old.md   a deep doc mentioning tasks/reference/x.md

(require 'ert)
(require 'package)
(defvar bill/test-elpa)
(defvar bill/test-subject)
(setq package-user-dir bill/test-elpa)
(package-initialize)
(require 'helm-files)
(require 'ffap)
(load-file bill/test-subject)

(defvar bill/test-root
  (let ((root (file-name-as-directory (make-temp-file "prfap-" t))))
    (dolist (f '("tasks/reference/x.md" "tasks/reference/local.md" "reference/local.md"))
      (make-directory (file-name-directory (expand-file-name f root)) t)
      (write-region "" nil (expand-file-name f root)))
    (make-directory (expand-file-name "tasks/archive/2026/11/07" root) t)
    (write-region
     "a `tasks/reference/x.md` b `tasks/reference/x.md:42` c see tasks/reference/x.md. d `reference/local.md` e `tasks/nope.md`\n"
     nil (expand-file-name "tasks/foo.md" root))
    (write-region "see `tasks/reference/x.md` here\n" nil
                  (expand-file-name "tasks/archive/2026/11/07/old.md" root))
    (let ((default-directory root))
      (call-process "git" nil nil nil "init" "-q"))
    root)
  "The throwaway repo root.")

(defun bill/test-guess (doc needle &optional guesser)
  "Open DOC (repo-relative), put point inside the first NEEDLE, return GUESSER's result, expanded."
  (with-current-buffer (find-file-noselect (expand-file-name doc bill/test-root))
    (goto-char (point-min))
    (search-forward needle)
    (backward-char 3)
    ;; Expand inside the doc's buffer: a relative guess is relative to the doc.
    (prog1 (let ((guess (funcall (or guesser #'helm-ffap-guesser))))
             (and guess (expand-file-name guess)))
      (kill-buffer))))

(defun bill/test-truename (path) (and path (file-truename (expand-file-name path))))

(defconst bill/test-x (lambda () (file-truename (expand-file-name "tasks/reference/x.md" bill/test-root))))

(ert-deftest prfap-root-relative-name-resolves ()
  (should (equal (bill/test-truename (bill/test-guess "tasks/foo.md" "`tasks/reference/x.md`"))
                 (funcall bill/test-x))))

(ert-deftest prfap-line-number-suffix-is-stripped ()
  (should (equal (bill/test-truename (bill/test-guess "tasks/foo.md" "x.md:42"))
                 (funcall bill/test-x))))

(ert-deftest prfap-sentence-period-is-stripped ()
  (should (equal (bill/test-truename (bill/test-guess "tasks/foo.md" "x.md. d"))
                 (funcall bill/test-x))))

(ert-deftest prfap-file-relative-name-still-wins ()
  (should (equal (bill/test-truename (bill/test-guess "tasks/foo.md" "`reference/local.md`"))
                 (file-truename (expand-file-name "tasks/reference/local.md" bill/test-root)))))

(ert-deftest prfap-deep-archived-doc-resolves ()
  (should (equal (bill/test-truename (bill/test-guess "tasks/archive/2026/11/07/old.md" "x.md"))
                 (funcall bill/test-x))))

(ert-deftest prfap-nonexistent-name-is-not-resolved-to-a-file ()
  ;; A name that exists nowhere must not be turned into some other existing file.
  (let ((guess (bill/test-guess "tasks/foo.md" "nope.md")))
    (should-not (and guess (file-exists-p guess)))))

(ert-deftest prfap-plain-ffap-resolves-too ()
  (should (equal (bill/test-truename
                  (bill/test-guess "tasks/foo.md" "`tasks/reference/x.md`"
                                   (lambda () (ffap-file-at-point))))
                 (funcall bill/test-x))))

;;; check_helm_file_at_point.el ends here

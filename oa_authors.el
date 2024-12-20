(require 'plz)              ; Ensure you have the `plz` library loaded
(require 'json)             ; For parsing JSON
(require 'helm)             ; For using Helm


;; (setq xx (json-parse-string (plz 'get "https://api.openalex.org/authors?search=patrick%20brown")))

;; (setq results (gethash "results" xx))

;; (setq res1 (aref results 0))
;; (get-hashtable-keys res1)

;; (setq affs (gethash "affiliations" res1))

;; (setq aff0 (aref affs 0))

;; (get-hashtable-keys aff0)

;; (mapcar (lambda (x) (gethash "display_name" (gethash "institution" x))) affs)

;; (setq ins0 (gethash "institution" aff0))

;; (get-hashtable-keys ins0)
;; (gethash "display_name" ins0)

(defun get-hashtable-keys (hashtable)
  "Return a list of keys from HASHTABLE."
  (let (keys)
    (maphash (lambda (key value)
               (push key keys))  ; Collect keys in reverse order
             hashtable)
    (nreverse keys)))  ; Reverse to maintain original order

(setq skillz-values-to-extract '(;; ("id" . 20)
				  ("display_name" . 40)
				  ("relevance_score" . 10)
				  ("works_count" . 5)
				  ("cited_by_count" . 7)))


(defun skillz-insert-uva-oa-link (uva-author-id oa-author-id)
  ;; (message "uva-autor-id" uva-author-id)
  "actually write to the database the uva-oa links"

  (sqlite-execute skillz-con "insert into links_uva_oa values (?, ?)" (list uva-author-id oa-author-id)))
  


(defun skillz-author-search (uva-author-id)
  "search openalex authors and enter them into uva_people"
  ;; (interactive)
    
  (let* ( ;; generate url, download, parse to lisp
	  (initial-name (caar  (sqlite-select skillz-con "select name from uva_people where uva_author_id = ?" (list uva-author-id)) ))
	  (search-term (read-string "name: " initial-name)) ;; get initial names
	  (url (concat "https://api.openalex.org/authors?search=" (url-hexify-string search-term)))
	  (json-search-res (json-parse-string (plz 'get url)))
	  
	  ;; generate helm candidates: pseudo multiple column support by padding entries
	  (oa-candidates
	    (mapcar (lambda (search-result)
		      (cons (concat
			      (mapconcat (lambda (key)
					   (string-pad (format "%s" (gethash (car key) search-result)) (cdr key)))
				skillz-values-to-extract) ;; each search result gets reduced to one line
			      ;; (mapconcat (lambda (x) (gethash "display_name" (gethash "institution"
			      (mapconcat (lambda (x) (gethash "display_name" (gethash "institution" x)))
				(gethash "affiliations" search-result) ",")
			      )
			(gethash "id" search-result)
			))
	      (gethash "results" json-search-res)))
	  
	  ;; actual helm query
	  (helm-oa-sources (helm-build-sync-source "pick one"
			     :candidates oa-candidates
			     :action (lambda (whatever) ;; insert into sqlite db
				       (mapc (lambda (sel) (skillz-insert-uva-oa-link uva-author-id sel))
					 (helm-marked-candidates))))))
    (helm :sources '(helm-oa-sources)))
   
  )


(skillz-author-search "uva6")




    
;; (sqlite-execute skillz-con "select name from uva_people where uva_author_id = ?" ["uva3"])

;; (setq skillz-db "~/Dropbox/proj/skilz/skilz.sqlite")

;; (setq skillz-con (sqlite-open db-skillz))

;; (sqlite-execute con "CREATE TABLE if not exists 'uva_people' ('uva_author_id' string, 'name' string);")
;; (sqlite-execute con "CREATE TABLE if not exists 'links_uva_oa' ('uva_author_id' string, 'oa_author_id' string);")


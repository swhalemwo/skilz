
;; (defun skillz-dl-author-search (search-term)
;;   (with-temp-buffer
(setq xx (json-parse-string (plz 'get "https://api.openalex.org/authors?search=olav%20velthuis")))

(defun get-hashtable-keys (hashtable)
  "Return a list of keys from HASHTABLE."
  (let (keys)
    (maphash (lambda (key value)
               (push key keys))  ; Collect keys in reverse order
             hashtable)
    (nreverse keys)))  ; Reverse to maintain original order



    

(require 'plz)              ; Ensure you have the `plz` library loaded
(require 'json)             ; For parsing JSON
(require 'helm)             ; For using Helm

(defun skillz-dl-author-search (search-term)
  "Search for authors by SEARCH-TERM using the OpenAlex API."
  
    ;; Query the API
  (let* (
	 (url (concat "https://api.openalex.org/authors?search=" (url-hexify-string search-term))
	    (list-search-res))
	 (json-res (json-parse-string (plz 'get url)))
	 (candidates

	   
      ;; (message (format "%s" (point)))
      
      ;; Check for HTTP success; you might want to handle errors more robustly
      ;; (when (looking-at "HTTP/1.[01] 200 OK")
        ;; Parse the JSON response in the temporary buffer
        (let* ((json-object-type 'hash)
               (json-array-type 'list)
               (json (json-read))
               (authors (gethash "results" json))) ; Getting the list of authors from the JSON response

          ;; Optionally process the authors list or structure
          (let ((author-names (mapcar (lambda (author)
                                         (gethash "display_name" author)) ; Extract the display_name field
                                       authors)))
            ;; Use Helm to allow user to select an author
            (helm :sources
                  (helm-build-sync-source "Select Author"
                    :candidates author-names
                    :action (lambda (name)
                              (message "You selected: %s" name)))))))))

;; Example usage
(skillz-dl-author-search "carl sagan")

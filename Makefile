deploy:
	rsync -avhzL --delete \
		--no-perms --no-owner --no-group \
		--exclude .git \
		--filter=":- .gitignore" \
		-e "ssh -i ~/Downloads/johnny_vu.pem" \
		. ubuntu@35.174.193.245:~/gnosis/safe-transaction-service

 payload = {'addUser': [{'account': {'accountId': account_id},
                                'billingCodes': [{'billingCodeId': billing_code}],
                                'groups':[{'groupId': group}],
                                'familyName': parsed["family_name"],
                                'givenName': parsed["given_name"],
                                'sshPublicKey': parsed["ssh_key"],
                                'password': parsed["password"],
                                'windows_password': parsed.get('windows_password'),
                                'email': parsed["email_address"]}]}

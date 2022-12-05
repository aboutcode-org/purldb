============================================================================
Install, configure, update and manage clearcode server instances with Ansible
============================================================================

To setup or update the clearcode instances first follow these instructions.

To provision and deploy an instance of clearcode, run::

    ansible-playbook -i hosts --verbose --ask-become-pass site.yml


You will be prompted for the password of your remote user on the clearcode server
for sudo access. Note: You may also have to add the `--ask-pass` flag if you have not
added you ssh public key to your user's authorized_keys file. You will also be prompted
for the vault password that is used to decrypt secrets (usernames, passwords, etc.) used
to set up services. This password is the same as the SSH deployment key password.

`--verbose` is for verbose output. You can remove it when you want less verbosity.

If your clearcode server user is not the same as your local user use instead::

    ansible-playbook -i hosts --verbose --user=<your username on clearcode> --ask-become-pass site.yml


Common operations
-----------------


Local testing in a VM
~~~~~~~~~~~~~~~~~~~~~
For local testing in a VM, first install a bare VM with Ubuntu Serevr 16.X LTS.
You only need the OpenSSH server and need to be able to SSH in the VM.
This is typically achieved by using Bridge Networking in VirtualBox.

- SSH in the VM to get its IP address with `$ ifconfig`.
- Given an IP of ww.xx.yy.zz, update the `hosts-test` sample host file with this local IP,
  e.g. the IP of your VM in a [testvm] role
  Do NOT use the `hosts` inventory file in you ansible commands.
- Then you can run ansible with this test config using your VM user password that will be
  asked twice. You may need to have `sshpass` installed. Or you can setup SSH key auth
  otherwise for password-less SSH'ing in the VM.::

    ansible-playbook -i hosts-test ---verbose --ask-become-pass site.yml

When testing you may want to locally change the vars.yml playbook to fetch
alternative test branches.

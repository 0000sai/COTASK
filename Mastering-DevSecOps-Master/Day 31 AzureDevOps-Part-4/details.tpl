[docker_servers]
${master01} ansible_ssh_private_key_file=/home/adminsai/myagent/_work/2/s/SecOps-Key.pem
${master02} ansible_ssh_private_key_file=/home/adminsai/myagent/_work/2/s/SecOps-Key.pem
${master03} ansible_ssh_private_key_file=/home/adminsai/myagent/_work/2/s/SecOps-Key.pem
[docker_master]
${master01} ansible_ssh_private_key_file=/home/adminsai/myagent/_work/2/s/SecOps-Key.pem
[docker_managers]
${master02} ansible_ssh_private_key_file=/home/adminsai/myagent/_work/2/s/SecOps-Key.pem
${master03} ansible_ssh_private_key_file=/home/adminsai/myagent/_work/2/s/SecOps-Key.pem
[docker_workers]
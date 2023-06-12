
def fetch_repo_addons():
    global addons_repo_dir, repo_addons, service_dir
    if not repo_addons:
        return
    exec_ssh(f"mkdir -p {addons_repo_dir}")

    # Create each repo
    for repo_url, repo_name in set(repo_addons.keys()):
        repo_dir = f"{addons_repo_dir}/{repo_name}"
        exec_ssh(f'if cd {repo_dir}; then git pull; else git clone {repo_url} {repo_dir}; f')

    for repo, addons in repo_addons.items():
        repo_url, repo_name = repo
        repo_dir = f"{addons_repo_dir}/{repo_name}"
        for addon in addons:
            addon_dir = f"{repo_dir}/addons/{addon}"
            # Copy to the existing odoo instance at service_dir/addons
            # Delete the existing addon first
            exec_ssh(f"rm -rf {service_dir}/addons/{addon}")
            exec_ssh(f"cp -r {addon_dir} {service_dir}/addons/{addon}")
            
from chronogit.git_parser import parse_repo

def main(repo_path):
    commits = parse_repo(repo_path)
    print(f"Total commits parsed: {len(commits)}")

if __name__ == "__main__":
    import sys
    main(sys.argv[1])
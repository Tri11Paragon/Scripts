let 
	pkgs = import <nixpkgs> {}; 
in pkgs.mkShell {
	packages = [
		pkgs.git
		(pkgs.python3.withPackages (python-pkgs: [
			python-pkgs.requests
		]))
	];
}

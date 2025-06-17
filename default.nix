let 
	pkgs = import <nixpkgs> {}; 
in pkgs.mkShell {
	packages = [
		pkgs.git
		(pkgs.python3.withPackages (python-pkgs: [
			python-pkgs.requests
			python-pkgs.python-uinput
			python-pkgs.evdev
			python-pkgs.pyqt5
		]))
	];
}

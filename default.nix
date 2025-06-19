let 
	pkgs = import <nixpkgs> {}; 
in pkgs.mkShell {
	nativeBuildInputs = with pkgs; [ qt5.qttools.dev python3Packages.autopep8 python3Packages.flake8 ];
	propagatedBuildInputs = with pkgs; [
	    (python3.withPackages (ps: with ps; [
	    	pyqt5
			evdev
			python-uinput
	    ]))
	];

	packages = with pkgs; [
		git
		(python3.withPackages (python-pkgs: with python-pkgs; [
			requests
			python-uinput
			evdev
			pyqt5
		]))
		python3Packages.pyqt5
		python3Packages.pip
		libsForQt5.qt5.qtbase
		libsForQt5.qt5.qtx11extras
        qt5.qtbase
        qt5.wrapQtAppsHook
		qt5.qtx11extras
	];

	QT_QPA_PLATFORM_PLUGIN_PATH="${pkgs.qt5.qtbase.bin}/lib/qt-${pkgs.qt5.qtbase.version}/plugins";
}

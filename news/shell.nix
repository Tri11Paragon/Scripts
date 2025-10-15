let
  pkgs = import <nixpkgs> {config.allowUnfree = true;};
in pkgs.mkShell {
  nativeBuildInputs = with pkgs; [
    playwright-driver.browsers
  ];

  packages = with pkgs; [
    (python3.withPackages (python-pkgs: with python-pkgs; [
      ollama
      requests
      discordpy
      python-dotenv
      trafilatura
      playwright
	  flask
	  quart
	  transformers
	  datasets
      sentencepiece
      torchWithRocm
      huggingface-hub
      hf-xet
	  pip
	  (opencv4.override { enableGtk2 = true; enableFfmpeg = true; enableGStreamer = true; enableJPEG = true; ffmpeg = pkgs.ffmpeg-full; })
    ]))
  ];
  propagatedBuildInputs = with pkgs; [
		xorg.libX11
		xorg.libX11.dev
		xorg.libXcursor
		xorg.libXcursor.dev
		xorg.libXext
		xorg.libXext.dev
		xorg.libXinerama
		xorg.libXinerama.dev
		xorg.libXrandr
		xorg.libXrandr.dev
		xorg.libXrender
		xorg.libXrender.dev
		xorg.libxcb
		xorg.libxcb.dev
		xorg.libXi
		xorg.libXi.dev
		harfbuzz
		harfbuzz.dev
		zlib
		zlib.dev
		bzip2
		bzip2.dev
		pngpp
		brotli
		brotli.dev
		pulseaudio.dev
		git
		libGL
		libGL.dev
		glfw
	];
	LD_LIBRARY_PATH="/run/opengl-driver/lib:/run/opengl-driver-32/lib";
	shellHook = ''
      export PLAYWRIGHT_BROWSERS_PATH=${pkgs.playwright-driver.browsers}
      export PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=true
    '';
}

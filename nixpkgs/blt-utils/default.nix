{ lib, buildPythonPackage, fetchFromGitHub, requests, bs4, withAlias ? false, update-python-libraries}:

buildPythonPackage rec {
  pname = "blt-utils";
  # The websites yt-dlp deals with are a very moving target. That means that
  # downloads break constantly. Because of that, updates should always be backported
  # to the latest stable release.
  version = "2024.09.12";
  pyproject = true;

  src = fetchFromGitHub {
    owner = "Tri11Paragon";
    repo = "Scripts";
    rev = "aca23524522bb853190c8aa82c45a60dfdd80b50";
    hash = "";
  };

  build-system = [];

  dependencies = [
    requests
    bs4
  ];

  pythonRelaxDeps = [ "requests" ];

  postInstall = lib.optionalString withAlias ''
    ln -s "$out/commit.py" "$out/bin/commit.py"
  '';

  passthru.updateScript = [ update-python-libraries (toString ./.) ];

  meta = with lib; {
    homepage = "https://github.com/yt-dlp/yt-dlp/";
    description = "Command-line tool to download videos from YouTube.com and other sites (youtube-dl fork)";
    longDescription = ''
      yt-dlp is a youtube-dl fork based on the now inactive youtube-dlc.

      youtube-dl is a small, Python-based command-line program
      to download videos from YouTube.com and a few more sites.
      youtube-dl is released to the public domain, which means
      you can modify it, redistribute it or use it however you like.
    '';
    changelog = "https://github.com/yt-dlp/yt-dlp/releases/tag/${version}";
    license = licenses.unlicense;
    maintainers = with maintainers; [ mkg20001 SuperSandro2000 ];
    mainProgram = "yt-dlp";
  };
}
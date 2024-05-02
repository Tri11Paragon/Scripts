#!/bin/python3

import argparse
import subprocess
import util.color_io as color_io
import sys

parser = argparse.ArgumentParser(prog='WebASM Generator', description='Creates a webpage to run a WebASM Project, designed for use with emscripten', epilog='Meow')

parser.add_argument("-i", "--install", nargs='?', const="/var/www/html/", default=None)
if ("--install" in sys.argv or "-i" in sys.argv):
    parser.add_argument("file", default=None)

args = parser.parse_args()

f = sys.stdout

html_base = """
<!DOCTYPE html>
<html>
    <head>
        <meta charset="utf-8">
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>${TITLE HERE}</title>
        <style>
            body {
                margin: 0;
                padding: 0;
                height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                background-color: #222;
            }

            .loading-container {
                width: 80%;
                max-width: 600px;
            }

            .loading-text-container {
                width: 100%;
                display: flex;
                justify-content: center;
            }

            .loading-bar-container {
                width: 100%;
                height: 20px;
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                overflow: hidden;
            }

            .loading-bar {
                width: 0;
                height: 100%;
                background-color: #007bff;
                transition: width 0.5s ease-in-out;
            }

            .seperator {
                margin-top: 10px;
            }

            .progress-text {
                font-size: 20px;
                color: #fff;
            }

            .progress-text p {
                margin: 0px;
                display: inline;
            }

            div.canvas {
                display: none;
                margin: 0px;
                padding: 0px;
                width: 100%;
                height: 100%;
            }
            canvas.canvas {
                margin: 0px;
                padding: 0px;
            }
        </style>
    </head>
    <body>
        <div class="loading-container" id="loading-container">
            <div class="loading-bar-container">
                <div class="loading-bar" id="loadingBar1"></div>
            </div>
            <div class="seperator"></div>
            <div class="loading-text-container">
                <div class="progress-text" id="progressIndicator"></div>
            </div>
            <div class="loading-text-container">
                <div class="progress-text" id="progressText"></div>
            </div>
        </div>
        <div class="canvas" id="canvas-container">
            <canvas class="canvas" id="canvas" oncontextmenu="event.preventDefault()" width=100% height=100%, tabindex=-1></canvas>
        </div>
        <script type="text/javascript">
            var canvas = document.getElementById("canvas");
            const loadingBar1 = document.getElementById('loadingBar1');

            const progressText = document.getElementById('progressText');
            const progressIndicator = document.getElementById('progressIndicator');
            const loadingContainer = document.getElementById('loading-container');
            const canvasContainer = document.getElementById('canvas-container');

            var Module = {
                totalDependencies: 0,
                preRun: [],
                postRun: [],
                print: (function() {
                    return function(text) {
                        if (arguments.length > 1) 
                            text = Array.prototype.slice.call(arguments).join(' ');
                        console.log(text);
                    };
                })(),
                printErr: (function() {
                    return function(text){
                        if (arguments.length > 1) 
                            text = Array.prototype.slice.call(arguments).join(' ');
                        console.error(text);
                    };
                })(),
                canvas: (function() {
                    var canvas = document.getElementById('canvas');

                    // As a default initial behavior, pop up an alert when webgl context is lost. To make your
                    // application robust, you may want to override this behavior before shipping!
                    // See http://www.khronos.org/registry/webgl/specs/latest/1.0/#5.15.2
                    canvas.addEventListener("webglcontextlost", function(e) { 
                        alert('WebGL context lost. You will need to reload the page.'); 
                        e.preventDefault(); 
                    }, false);

                    return canvas;
                })(),
                setStatus: function(left) {
                    if (this.totalDependencies == 0)
                        return;
                    if (typeof left !== "number"){
                        if (left.includes("Download")){
                            progressIndicator.innerHTML = left;
                            progressText.innerText = "";
                            let open = left.lastIndexOf("(");
                            let close = left.lastIndexOf(")");
                            let progressFull = left.substring(open + 1, close);
                            let progressData = progressFull.split("/");
                            let downloaded = parseInt(progressData[0]);
                            let totalDownload = parseInt(progressData[1]);
                            let percentProgress = Math.round(Math.min((downloaded / totalDownload) * 100, 100));
                            loadingBar1.style.width = `${percentProgress}%`;
                            progressText.innerText = `${percentProgress}%`;
                        } else {
                            // Hide loading bar container
                            loadingContainer.style.display = 'none'; 
                            // show the canvas
                            canvasContainer.style.display = 'block';
                        }
                        return;
                    }
                    let progress = (this.totalDependencies - left) / this.totalDependencies;
                    let percentProgress = Math.round(Math.min(progress * 100, 100));
                    progressText.innerText = `${percentProgress}%`;
                    progressIndicator.innerHTML = `Loading Content (<p id="progressContent">0/0</p>)`;
                    const progressContent = document.getElementById('progressContent');
                    progressContent.innerText = `${this.totalDependencies - left}/${this.totalDependencies}`;
                },
                monitorRunDependencies: function(left) {
                    this.totalDependencies = Math.max(this.totalDependencies, left);
                    Module.setStatus(left);
                }
            };

            window.onerror = function() {
                Module.setStatus = function(text) {
                    if (text)
                        console.error('[post-exception status] ' + text);
                };
            };
        </script>
        <script async type="text/javascript" src="${SCRIPT_HERE}"></script>
    </body>
</html>
"""

if args.install:
    path = args.install
    if not args.install.endswith("/"):
        path += "/"
    path += args.file
    if not args.file.endswith(".html"):
        path += ".html"
    f = open(path, "wt")

def bprint(*args, **kwargs):
    print(*args, file=f, **kwargs)

if __name__ == "__main__":
    html_out = html_base.replace("${TITLE_HERE}", color_io.input_print("Please enter page title"));
    html_out = html_out.replace("${SCRIPT_HERE}", color_io.input_print("Please enter script location and name"));
    
    bprint(html_out);
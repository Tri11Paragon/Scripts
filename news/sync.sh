#!bash
rsync -a models/ brett@index:~/models

for f in models/*.modelfile; do
	echo "Updating model: $f"
	filename="${f##*/}"
	basename="${filename%.*}"
	echo "Model name: $basename from $filename"
	ssh brett@index "ollama rm $basename && ollama create $basename -f \~/$f"
done

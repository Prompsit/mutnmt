from app import app
import tempfile
import subprocess
import os


class MarianWrapper:
    def __init__(self, engine_path):
        self.model = str(engine_path) + "/model.npz.best-bleu.npz.decoder.yml"

    def translate(self, lines, n_best=False):
        translations = []
        output_tmp = tempfile.NamedTemporaryFile(delete=False)
        n_best_flag = "--n-best" if n_best else ""
        input_tmp = tempfile.NamedTemporaryFile(delete=False)
        lines = [line.rstrip("\n") + "\n" for line in lines]
        with open(input_tmp.name, "w") as f:
            f.writelines(lines)

        marian_cmd = (
            "cat {0} | {1}/build/marian-decoder -c {2} {3} -w 4000 > {4}".format(
                input_tmp.name,
                app.config["MARIAN_FOLDER"],
                self.model,
                n_best_flag,
                output_tmp.name,
            )
        )

        print("----------------------------", flush = True)
        print("MARIAN TRANSLATE COMMAND", flush = True)
        print(marian_cmd, flush = True)
        print("----------------------------", flush = True)

        try:
            subprocess.run(marian_cmd, shell=True, capture_output=True, check=True)
        except Exception as e:
            raise Exception from e
        with open(output_tmp.name, "r") as temp_file:
            translations = [line.rstrip("\n") for line in temp_file.readlines()]
        os.remove(input_tmp.name)
        os.remove(output_tmp.name)
        return translations

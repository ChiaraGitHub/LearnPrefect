import datetime
import os
import imageio
from io import BytesIO

import prefect
from prefect import task
from prefect.engine.signals import SKIP
from prefect.tasks.shell import ShellTask

from prefect import Parameter, Flow

from dask.distributed import Client
from prefect.engine.executors import DaskExecutor


@task
def curl_cmd(url: str, fname: str) -> str:
    """
    The curl command we wish to execute.
    """
    if os.path.exists(fname):
        raise SKIP("Image data file already exists.")
    return "curl -fL -o {fname} {url}".format(fname=fname, url=url)


# ShellTask is a task from the Task library which will execute a given command in a subprocess
# and fail if the command returns a non-zero exit code
download = ShellTask(name="curl_task", max_retries=2, retry_delay=datetime.timedelta(seconds=10))

@task(skip_on_upstream_skip=False)
def load_and_split(fname: str) -> list:
    """
    Loads image data file at `fname` and splits it into
    multiple frames.  Returns a list of bytes, one element
    for each frame.
    """
    with open(fname, "rb") as f:
        images = f.read()
        
    return [img for img in images.split(b"\n" * 4) if img]

@task
def write_to_disk(image: bytes) -> bytes:
    """
    Given a single image represented as bytes, writes the image
    to the present working directory with a filename determined
    by `map_index`.  Returns the image bytes.
    """
    frame_no = prefect.context.get("map_index")
    with open("output_images/frame_{0:0=2d}.gif".format(frame_no), "wb") as f:
        f.write(image)
    return image




@task
def combine_to_gif(image_bytes: list) -> None:
    """
    Given a list of ordered images represented as bytes,
    combines them into a single GIF stored in the present working directory.
    """
    images = [imageio.imread(BytesIO(image)) for image in image_bytes]
    imageio.mimsave('output_images/clip.gif', images)




DATA_URL = Parameter("DATA_URL", 
                     default="https://github.com/cicdw/image-data/blob/master/all-images.img?raw=true")

DATA_FILE = Parameter("DATA_FILE", default="output_images/image-data.img")


with Flow("Image ETL") as flow:
    
    # Extract
    command = curl_cmd(DATA_URL, DATA_FILE)
    curl = download(command=command)
    
    # Transform
    # we use the `upstream_tasks` keyword to specify non-data dependencies
    images = load_and_split(fname=DATA_FILE, upstream_tasks=[curl])
    
    # Load  
    frames = write_to_disk.map(images)
    result = combine_to_gif(frames)
    
# flow.run()
# Run
if __name__ == '__main__':
    client = Client(n_workers=4, threads_per_worker=1)
    executor = DaskExecutor(address=client.scheduler.address)
    flow.run(executor=executor)
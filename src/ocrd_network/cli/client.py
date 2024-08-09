import click
from json import dumps, loads
from typing import Optional
from ocrd.decorators import parameter_option
from ocrd_utils import DEFAULT_METS_BASENAME
from ..client import Client


@click.group('client')
def client_cli():
    """
    A client for interacting with the network modules.
    The client CLI mimics the WebAPI endpoints
    """
    pass


@client_cli.group('discovery')
def discovery_cli():
    """
    The discovery endpoint of the WebAPI
    """
    pass


@client_cli.group('processing')
def processing_cli():
    """
    The processing endpoint of the WebAPI
    """
    pass


@processing_cli.command('processor')
@click.argument('processor_name', required=True, type=click.STRING)
@click.option('--address')
@click.option('-m', '--mets', required=True, default=DEFAULT_METS_BASENAME)
@click.option('-I', '--input-file-grp', default='OCR-D-INPUT')
@click.option('-O', '--output-file-grp', default='OCR-D-OUTPUT')
@click.option('-g', '--page-id')
@parameter_option
@click.option('--result-queue-name')
@click.option('--callback-url')
@click.option('--agent-type', default='worker')
@click.option('-b', '--block-till-job-end', default=False)
def send_processing_job_request(
    address: Optional[str],
    processor_name: str,
    mets: str,
    input_file_grp: str,
    output_file_grp: Optional[str],
    page_id: Optional[str],
    parameter: Optional[dict],
    result_queue_name: Optional[str],
    callback_url: Optional[str],
    # TODO: This is temporally available to toggle
    #  between the ProcessingWorker/ProcessorServer
    agent_type: Optional[str],
    block_till_job_end: Optional[bool]
):
    req_params = {
        "path_to_mets": mets,
        "description": "OCR-D Network client request",
        "input_file_grps": input_file_grp.split(','),
        "parameters": parameter if parameter else {},
        "agent_type": agent_type
    }
    if output_file_grp:
        req_params["output_file_grps"] = output_file_grp.split(',')
    if page_id:
        req_params["page_id"] = page_id
    if result_queue_name:
        req_params["result_queue_name"] = result_queue_name
    if callback_url:
        req_params["callback_url"] = callback_url
    client = Client(server_addr_processing=address)
    processing_job_id = client.send_processing_job_request(
        processor_name=processor_name, req_params=loads(dumps(req_params)))
    assert processing_job_id
    print(f"Processing job id: {processing_job_id}")
    if block_till_job_end:
        client.poll_job_status_till_timeout_fail_or_success(job_id=processing_job_id)


@client_cli.group('workflow')
def workflow_cli():
    """
    The workflow endpoint of the WebAPI
    """
    pass


@processing_cli.command('run')
@click.option('--address')
@click.option('-m', '--path-to-mets', required=True)
@click.option('-w', '--path-to-workflow', required=True)
@click.option('-b', '--block-till-job-end', default=False)
def send_workflow_job_request(
    address: Optional[str],
    path_to_mets: str,
    path_to_workflow: str,
    block_till_job_end: Optional[bool]
):
    client = Client(server_addr_processing=address)
    workflow_job_id = client.send_workflow_job_request(path_to_wf=path_to_workflow, path_to_mets=path_to_mets)
    assert workflow_job_id
    print(f"Workflow job id: {workflow_job_id}")
    if block_till_job_end:
        client.poll_wf_status_till_timeout_fail_or_success(job_id=workflow_job_id)


@client_cli.group('workspace')
def workspace_cli():
    """
    The workspace endpoint of the WebAPI
    """
    pass

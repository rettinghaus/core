# Abstraction for the Processing Server unit in this arch:
# https://user-images.githubusercontent.com/7795705/203554094-62ce135a-b367-49ba-9960-ffe1b7d39b2c.jpg

# Calls to native OCR-D processor should happen through
# the Processing Worker wrapper to hide low level details.
# According to the current requirements, each ProcessingWorker
# is a single OCR-D Processor instance.
class ProcessingWorker:
    def __init__(self):
        # RMQConsumer object must be created here, reference: RabbitMQ Library (WebAPI Implementation)
        # Based on the API calls the ProcessingWorker will receive messages from the running instance
        # of the RabbitMQ Server (deployed by the Processing Broker) through the RMQConsumer object.
        self.rmq_consumer = self.configure_consumer(
            config_file=None,
            callback_method=self.on_consumed_message
        )

    @staticmethod
    def configure_consumer(config_file, callback_method):
        rmq_consumer = "RMQConsumer Object"
        """
        Here is a template implementation to be adopted later
        
        rmq_consumer = RMQConsumer(host="localhost", port=5672, vhost="/")
        # The credentials are configured inside definitions.json
        # when building the RabbitMQ docker image
        rmq_consumer.authenticate_and_connect(
            username="default-consumer",
            password="default-consumer"
        )
        # The callback method is called every time a message is consumed
        rmq_consumer.configure_consuming(queue_name="queue_name", callback_method=funcPtr)
        
        """
        return rmq_consumer

    # Define what happens every time a message is consumed from the queue
    def on_consumed_message(self):
        pass

    # A separate thread must be created here to listen
    # to the queue since this is a blocking action
    def start_consuming(self):
        # Blocks here and listens for messages coming from the specified queue
        # self.rmq_consumer.start_consuming()
        pass

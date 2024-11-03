from testcontainers.core.container import DockerContainer

TEST_ZONE_FILE_DIRECTORY = "/var/opt/isc/scls/isc-bind/zones/"
TEST_ZONE_FILE_PATH = "/var/opt/isc/scls/isc-bind/zones/_default.nzf"


class UnixContainer:
    __test__ = False

    def __init__(self):
        self.container = DockerContainer("ubuntu:latest").with_command(
            "tail -f /dev/null"
        )
        self.container.start()

    def __run_command(self, command):
        cmd = ["bash", "-c", f"{command}"]
        print(cmd)
        execRes = self.container.exec(cmd)
        output = execRes.output.decode("utf-8").strip()
        return output

    def create_zone_file_directory(self):
        command = f"mkdir -p {TEST_ZONE_FILE_DIRECTORY}"
        self.__run_command(command)

    def create_zone_file(self):
        command = f"touch {TEST_ZONE_FILE_PATH}"
        self.__run_command(command)

    def populate_zone_file(self):
google.com
        self.__run_command(command)

    def prepare_zonefile(self):
        self.create_zone_file_directory()
        self.create_zone_file()
        self.populate_zone_file()
        return self

    def stop(self):
        self.container.stop()

    def run_cmd(self, cmd: str) -> str:
        return self.__run_command(cmd)

from gibs import Wms

if __name__ == "__main__":
    wms = Wms()
    wms.getCapabilities('output.tsv')
    wms.download()



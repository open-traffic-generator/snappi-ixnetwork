import utils


def captures_ok(api, cfg, size, src, dst):
    """
    Returns normally if patterns in captured packets are as expected.
    """
    cap_dict = utils.get_all_captures(api, cfg)
    src_list = []
    dst_list = []
    length = []
    for k in cap_dict:
        for b in cap_dict[k]:
            dst_list.append(
                ":".join(['{:02X}'.format(byt) for byt in b[0:6]])
            )
            src_list.append(
                ":".join(['{:02X}'.format(byt) for byt in b[6:12]])
            )
            length.append(len(b))

    assert sorted(src_list) == sorted(src) and sorted(dst_list) == sorted(dst)
    assert length == size

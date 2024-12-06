import cco_writers
import cco_concurrency_finders
import cco_partialorder_handlers
from tqdm import tqdm
import pandas as pd


from Concurrent import Concurrent


def transform(
    filog_towrite,
    mode,
    scope,
    vars,
    vars_wlc,
    stats_only,
    caseid_dict,
    keyword_c,
    keyword_s,
):
    """Transforms sequential input log to partially ordered output log
    based on defined concurrency oracle parameters.
    """

    successors = {}
    concurrent = Concurrent()

    povariants = []
    sequentialvariants = vars.keys()
    sequentialvariants_w_lcinfo = vars_wlc.keys()

    if scope == "logwise":  # extract logwise concurrency in pre-run
        if mode == "alpha":
            seqv = sequentialvariants
            for v in tqdm(seqv, desc="analyzing concurrency, completed variants:"):
                successors, concurrent = cco_concurrency_finders.findAlphaConcurrency(
                    v, successors, concurrent
                )
        elif mode == "lifecycle":
            seqv_wlc = sequentialvariants_w_lcinfo
            for v in seqv_wlc:
                finder = cco_concurrency_finders.LifecycleConcurrencyFinder(
                    v, keyword_c, keyword_s
                )
                result = finder.find()
                concurrent = concurrent.union(result["concurrencies"])

        else:
            raise NotImplementedError()

    elif scope == "tracewise":
        pass
    else:
        raise NotImplementedError()

    if (
        scope == "logwise"
    ):  # use extracted concurrency information to build partially ordered traces
        # in case of logwise concurrency detection, print report on console and export as .csv
        print("")
        print("The following concurrencies were detected:")
        if len(concurrent) > 0:
            for c in concurrent.to_tuples():
                print(c)
            export_df = pd.DataFrame(
                concurrent.to_tuples(), columns=["activity_1", "activity_2"]
            )
            export_df.to_csv("concurrencies.csv", index=False)
        else:
            print("No concurrencies found in the log.")

        po_id = 1

        for var in tqdm(
            sequentialvariants, desc="generating partially ordered traces: "
        ):
            potn, partialorder, pograph = (
                cco_partialorder_handlers.createPObyactivities_NxDiGraph(
                    var, concurrent
                )
            )  # generate partial orders using log-concurrency info

            poname_towrite, po_id, timeout = (
                cco_partialorder_handlers.check_for_po_isomorphs(
                    partialorder, po_id, pograph, povariants
                )
            )  # check partial orders for isomorphy with already found partial orders

            if not stats_only:
                caseids_akt_var = caseid_dict[var]
                filog_towrite = cco_writers.writePOinfo(
                    filog_towrite, caseids_akt_var, potn, poname_towrite
                )

    elif scope == "tracewise":
        if mode == "alpha":
            report_concurrency = Concurrent()
            po_id = 1

            for var in tqdm(
                sequentialvariants,
                desc="find concurrency and generate partially ordered traces, completed: ",
            ):
                successors, concurrent = cco_concurrency_finders.findAlphaConcurrency(
                    var
                )
                report_concurrency = report_concurrency.union(concurrent)

                potn, partialorder, pograph = (
                    cco_partialorder_handlers.createPObyactivities_NxDiGraph(
                        var, concurrent
                    )
                )

                poname_towrite, po_id, timeout = (
                    cco_partialorder_handlers.check_for_po_isomorphs(
                        partialorder, po_id, pograph, povariants
                    )
                )

                if not stats_only:
                    caseids_variant = caseid_dict[var]
                    filog_towrite = cco_writers.writePOinfo(
                        filog_towrite, caseids_variant, potn, poname_towrite
                    )

            print("")
            print("Concurrent in at least one trace variant:")
            if len(report_concurrency) > 0:
                for c in report_concurrency.to_tuples():
                    print(c)
                export_df = pd.DataFrame(
                    report_concurrency.to_tuples(), columns=["activity_1", "activity_2"]
                )
                export_df.to_csv("concurrencies.csv", index=False)
            else:
                print("No concurrencies found in the log.")

        elif mode == "lifecycle":
            po_id = 1
            for var in tqdm(
                sequentialvariants_w_lcinfo,
                desc="find concurrency and generate partially ordered traces: ",
            ):
                finder = cco_concurrency_finders.LifecycleConcurrencyFinder(
                    var, keyword_c, keyword_s
                )
                result = finder.find()
                concurrent = concurrent.union(result["concurrencies"])
                pos_concurrent = result["positional_concurrencies"]
                equis = result["positional_equivalences"]

                potn, partialorder, pograph = (
                    cco_partialorder_handlers.createPObypositions_NxDiGraph(
                        var, pos_concurrent, equis
                    )
                )

                poname_towrite, po_id, timeout = (
                    cco_partialorder_handlers.check_for_po_isomorphs(
                        partialorder, po_id, pograph, povariants
                    )
                )

                if not stats_only:
                    caseids_variant = caseid_dict[var]
                    filog_towrite = cco_writers.writePOinfo(
                        filog_towrite, caseids_variant, potn, poname_towrite
                    )

            print("")
            print("Concurrent in at least one trace variant:")
            if len(concurrent) > 0:
                for c in concurrent.to_tuples():
                    print(c)
                export_df = pd.DataFrame(
                    concurrent.to_tuples(), columns=["activity_1", "activity_2"]
                )
                export_df.to_csv("concurrencies.csv", index=False)
            else:
                print("No concurrencies found in the log.")

        else:
            raise NotImplementedError()
    else:
        raise NotImplementedError()

    print("")
    print("***")
    print("ANALYSIS RESULTS:")
    print("***")
    print("Number of partially ordered variants:")
    print(len(povariants))

    return filog_towrite, povariants

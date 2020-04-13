__author__ = 'Marcelo Ferreira da Costa Gomes'

import argparse
import datetime
import glob
import logging
import os
import smtplib
from argparse import RawDescriptionHelpFormatter
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.encoders import encode_base64
from subprocess import run
from settings import EMAIL, SERVER, REPORT
from data_filter.episem import episem, lastepiweek


logger = logging.getLogger('update_system')
logger.setLevel(logging.DEBUG)
logger_fname = 'InfoGripe_system_update.log'
fh = logging.FileHandler(logger_fname)
ch = logging.StreamHandler('InfoGripe_system_update.error.log')
ch.setLevel(logging.ERROR)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)
logger.addHandler(fh)
logger.addHandler(ch)


mail_error = {
    'subject': "InfoGripe Updater -- error log",
    'email_body': """
    This is an automated message from InfoGripe Updater.
    System's database update started at %(time)s raised an error at module %(mdl_name)s.
    Please check the attached log for details.

    All the best,
    InfoGripe Updater Monitor. 
    """,
    **EMAIL
}
mail_success = {
    'subject': "InfoGripe Updater -- success",
    'email_body': """
    This is an automated message from InfoGripe Updater.
    System's database update started at %(time)s ran without raising any errors.

    All the best,
    InfoGripe Updater Monitor. 
    """,
    **EMAIL
}

home_path = os.path.expanduser("~")
logfile_path = os.path.join(os.getcwd(), logger_fname)
data_folder = os.path.join(os.getcwd(), '..', 'data', 'data')
time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
timesmpl = datetime.datetime.now().strftime('%Y%m%d')
modules_list = ['all',
                'full_email_update',
                'email',
                'dbf2csv',
                'filter',
                'convert2mem',
                'estimator',
                'consolidate',
                'export',
                'report',
                'sendreport']


def send_email(mail_dict):
    module_name = 'send_email.settings'
    logger.info(module_name)

    email_msg = MIMEMultipart()
    email_msg['From'] = '%(NAME)s <%(USER)s>' % mail_dict
    email_msg['To'] = mail_dict['TO']
    email_msg['Subject'] = mail_dict['subject']
    body = MIMEText(mail_dict['email_body'], 'plain')
    email_msg.attach(body)
    fp = open(logfile_path, encoding='utf-8')
    attachment = MIMEText(fp.read(), 'text/plain')
    attachment.add_header("Content-Disposition", "attachment", filename=logger_fname)
    email_msg.attach(attachment)
    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.ehlo()
        server.login(EMAIL['USER'], EMAIL['PASSWORD'])
        server.send_message(email_msg)
        server.close()
    except Exception as exception:
        logger.exception(exception)
        raise

    return


def send_report_email(epiyear: int, epiweek: int):
    module_name = 'send_report_email.settings'
    logger.info(module_name)

    mail_report = {
        'subject': "[InfoGripe] Boletim da SE %s %02d" % (epiyear, epiweek),
        'email_body': """
Caro(a),
      
Segue o boletim semanal gerado automaticamente pelo InfoGripe, com base nos dados do Sivep-gripe até a SE %s %02d.
Esta é uma mensagem automática, não é necessário responder o e-mail.

Acesse o site para mais informações:
http://info.gripe.fiocruz.br

Atenciosamente,
Equipe InfoGripe
InfoGripe - http://info.gripe.fiocruz.br
FluDashboard - https://github.com/FluVigilanciaBR/fludashboard
""" % (epiyear, epiweek),
        **REPORT
    }

    email_msg = MIMEMultipart()
    email_msg['From'] = '%(NAME)s <%(USER)s>' % mail_report
    email_msg['Subject'] = mail_report['subject']
    body = MIMEText(mail_report['email_body'], 'plain')
    email_msg.attach(body)
    report_fname = 'Boletim_InfoGripe_SE%s%02d.pdf' % (epiyear, epiweek)
    fp = open(report_fname, 'rb')
    attachment = MIMEApplication(fp.read(), _subtype='pdf', _encoder=encode_base64)
    attachment.add_header("Content-Disposition", "attachment", filename=report_fname)
    email_msg.attach(attachment)
    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.ehlo()
        server.login(REPORT['USER'], REPORT['PASSWORD'])
        server.send_message(email_msg, to_addrs=mail_report['CCO'].split(', '))
        server.close()
    except Exception as exception:
        logger.exception(exception)
        raise

    logger.info('%s : DONE', module_name)
    return


def convert_dbf(flist):
    from data_filter import dbf2csv

    module_name = dbf2csv.__name__
    try:
        dbf2csv.main(flist)
    except Exception as err:
        logger.exception(module_name)
        logger.exception(err)
        mail_error['email_body'] = mail_error['email_body'] % {'time': time, 'mdl_name': module_name}
        send_email(mail_error)
        raise

    logger.info('%s : DONE', module_name)
    return


def email_update(dir, years):
    from data_filter import email_extract

    module_name = email_extract.__name__

    try:
        if years:
            for year in years:
                logger.info('Updating over e-mail. Base year: %s' % year)
                email_extract.main(dir, year)
        else:
            logger.info('Updating over e-mail.')
            email_extract.main(dir)

    except Exception as err:
        logger.exception(module_name)
        logger.exception(err)
        mail_error['email_body'] = mail_error['email_body'] % {'time': time, 'mdl_name': module_name}
        send_email(mail_error)
        raise

    logger.info('%s : DONE', module_name)
    return


def apply_filters(flist=None):
    from data_filter import sinan_filter_of_interest

    module_name = sinan_filter_of_interest.__name__

    if not flist:
        flist = sorted(glob.glob('../data/INFLUD*.csv'))

    logger.info('Historical files: %s', flist)
    try:
        sinan_filter_of_interest.main(flist)
    except Exception as err:
        logger.exception(module_name)
        logger.exception(err)
        mail_error['email_body'] = mail_error['email_body'] % {'time': time, 'mdl_name': module_name}
        send_email(mail_error)
        raise

    logger.info('%s : DONE', module_name)

    return


def add_epiweek():
    from data_filter import insert_epiweek

    module_name = insert_epiweek.__name__
    flist = ['clean_data_srag.csv', 'clean_data_sragflu.csv', 'clean_data_obitoflu.csv']
    for fname in flist:
        logger.info('Inserting epiweek on file %s' % fname)
        try:
            insert_epiweek.main(fname)
        except Exception as err:
            logger.exception(module_name)
            logger.exception(err)
            mail_error['email_body'] = mail_error['email_body'] % {'time': time, 'mdl_name': module_name}
            send_email(mail_error)
            raise

        logger.info('... DONE')

    logger.info('%s : DONE', module_name)
    return


def convert2mem():
    from data_filter import sinan_convert2mem

    module_name = sinan_convert2mem.__name__
    flist = ['../clean_data/clean_data_srag_epiweek.csv',
             '../clean_data/clean_data_sragflu_epiweek.csv',
             '../clean_data/clean_data_obitoflu_epiweek.csv']
    for fname in flist:
        logger.info('Converting to MEM structure: %s' % fname)
        try:
            sinan_convert2mem.main(fname)
        except Exception as err:
            logger.exception(module_name)
            logger.exception(err)
            mail_error['email_body'] = mail_error['email_body'] % {'time': time, 'mdl_name': module_name}
            send_email(mail_error)
            raise

        logger.info('... DONE')

    logger.info('%s : DONE', module_name)
    return


def apply_mem():
    from mem import sinan_mem_inset_thresholds

    module_name = sinan_mem_inset_thresholds.__name__
    dataset = ['srag', 'sragflu', 'obitoflu']
    for data in dataset:
        fname = '../clean_data/clean_data_%s_epiweek4mem-incidence.csv' % data
        logger.info('Calculating MEM thresholds for dataset: %s' % data)
        try:
            sinan_mem_inset_thresholds.main(fname)
        except Exception as err:
            logger.exception(module_name)
            logger.exception(err)
            mail_error['email_body'] = mail_error['email_body'] % {'time': time, 'mdl_name': module_name}
            send_email(mail_error)
            raise

        os.rename('../clean_data/mem-report.csv',
                  '../clean_data/%s_mem-report.csv' % data)
        os.rename('../clean_data/mem-typical.csv',
                  '../clean_data/%s_mem-typical.csv' % data)

        logger.info('... DONE')

    logger.info('%s : DONE', module_name)
    return


def apply_opportunities():
    from data_filter import delay_datasets, delay_table

    module_name = delay_datasets.__name__
    try:
        delay_datasets.main()
    except Exception as err:
        logger.exception(module_name)
        logger.exception(err)
        mail_error['email_body'] = mail_error['email_body'] % {'time': time, 'mdl_name': module_name}
        send_email(mail_error)
        raise

    module_name = delay_table.__name__
    try:
        fname = os.path.join(data_folder, 'delay_table.csv')
        delay_table.main(fname)
    except Exception as err:
        logger.exception(module_name)
        logger.exception(err)
        mail_error['email_body'] = mail_error['email_body'] % {'time': time, 'mdl_name': module_name}
        send_email(mail_error)
        raise


def apply_estimator(date='max'):
    from opportunity_estimator import add_situation2weekly_data

    dataset = ['srag', 'sragflu', 'obitoflu']
    Rscript = 'opportunity.estimator.R'

    for data in dataset:
        logger.info('Calculating estimates for dataset: %s' % data)
        module_name = 'opportunity_estimator.opportunity.estimator.R'
        try:
            run(['Rscript', '--vanilla', Rscript, '-d', date, '-t', data], check=True)
        except Exception as err:
            logger.exception(module_name)
            logger.exception(err)
            mail_error['email_body'] = mail_error['email_body'] % {'time': time, 'mdl_name': module_name}
            send_email(mail_error)
            raise

        logger.info('Adding situation info for dataset: %s' % data)
        try:
            add_situation2weekly_data.main([data])
        except Exception as err:
            logger.exception(module_name)
            logger.exception(err)
            mail_error['email_body'] = mail_error['email_body'] % {'time': time, 'mdl_name': module_name}
            send_email(mail_error)
            raise

        logger.info('... DONE')

    logger.info('opportunity_estimator : DONE')
    return


def consolidate(fname=None):
    from data_filter import consolidate_datasets
    from data_filter.settings import DATABASE

    module_name = consolidate_datasets.__name__
    try:
        consolidate_datasets.main(True)
    except Exception as err:
        logger.exception(module_name)
        logger.exception(err)
        mail_error['email_body'] = mail_error['email_body'] % {'time': time, 'mdl_name': module_name}
        send_email(mail_error)
        raise
    logger.info('%s : DONE', module_name)

    module_name = 'consolidate.pg_dump'
    try:
        if not fname:
            fname = os.path.join(data_folder, 'infogripe%s.dump' % timesmpl)
        run(['pg_dump', '-Fc', '--host=%(HOST)s' % DATABASE, '--username=%(USER)s' % DATABASE,
             '--dbname=%(NAME)s' % DATABASE, '-w', '--file', fname], check=True)
    except Exception as err:
        logger.exception(module_name)
        logger.exception(err)
        mail_error['email_body'] = mail_error['email_body'] % {'time': time, 'mdl_name': module_name}
        send_email(mail_error)
        raise

    logger.info('%s : DONE', module_name)
    return


def exportdb(fname=None):
    from time import sleep
    module_name = 'consolidate.export'
    tries = 10
    for i in range(tries):
        try:
            if not fname:
                fname = os.path.join(data_folder, 'infogripe%s.dump' % timesmpl)

            run(['scp', '-C', fname, '%(USER)s@%(HOST)s:~/update/infogripe.dump' % SERVER], check=True)
        except Exception as err:
            if i < tries - 1:  # i is zero indexed
                sleep(2)
                continue
            else:
                logger.exception(module_name)
                logger.exception(err)
                mail_error['email_body'] = mail_error['email_body'] % {'time': time, 'mdl_name': module_name}
                send_email(mail_error)
                raise
        break

    logger.info('%s : DONE', module_name)
    return


def generate_report(epiyear=None, epiweek=None, plot=None):

    Rscript = 'report.data.R'

    logger.info('Generating weekly report: %s %s' % (epiyear, epiweek))
    module_name = 'report.report.data.R'
    try:
        if plot:
            run(['Rscript', '--vanilla', Rscript, '-y', str(epiyear), '-w', str(epiweek), '-p'], check=True)
        else:
            run(['Rscript', '--vanilla', Rscript, '-y', str(epiyear), '-w', str(epiweek)], check=True)
    except Exception as err:
        logger.exception(module_name)
        logger.exception(err)
        mail_error['email_body'] = mail_error['email_body'] % {'time': time, 'mdl_name': module_name}
        send_email(mail_error)
        raise

    return


def main(flist=None, update_mem=False, module_list=None, history_files=None, dir=None, years=None, date='max',
         dbdump=None, plot=None):
    '''
    Run all scripts to update the system with new database.
    Optional: update MEM thresholds

    :param update_mem:
    :return:
    '''

    logger.info('System update: START')
    for m in module_list:
        if m not in modules_list:
            logger.error('Unknown module request: %s', m)
            mail_error['email_body'] = mail_error['email_body'] % {'time': time, 'mdl_name': 'caller'}
            send_email(mail_error)
            exit(0)

    if module_list and 'all' in module_list:
        module_list = ['dbf2csv',
                       'filter',
                       'convert2mem',
                       'estimator',
                       'consolidate',
                       'export',
                       'report',
                       'sendreport']
    if module_list and 'full_email_update' in module_list:
        module_list = ['email',
                       'filter',
                       'convert2mem',
                       'estimator',
                       'consolidate',
                       'export',
                       'report',
                       'sendreport']

    logger.info('Update MEM: %s', update_mem)
    logger.info('Update modules: %s', module_list)

    if 'dbf2csv' in module_list:
        logger.info('Module dbf2csv file list: %s', flist)
        logger.info('Convert DBF to CSV')
        convert_dbf(flist)

    os.chdir('./data_filter')

    if 'email' in module_list:
        logger.info('Emails update years: %s', years)
        email_update(dir, years)

    if 'filter' in module_list:
        logger.info('Aggregate and filter data')
        apply_filters(history_files)

    if 'epiweek' in module_list:
        logger.info('Insert epiweek')
        add_epiweek()

    if 'opportunities' in module_list:
        logger.info('Create table of opportunities')
        apply_opportunities()

    if 'convert2mem' in module_list:
        logger.info('Convert to MEM structure and aggregate by epiweek')
        convert2mem()

    os.chdir('../mem')
    if update_mem:
        logger.info('Apply MEM')
        apply_mem()

    os.chdir('../opportunity_estimator')
    if 'estimator' in module_list:
        logger.info('Apply opportunity estimator')
        apply_estimator(date)

    os.chdir('../data_filter')
    if 'consolidate' in module_list:
        logger.info('Consolidate dataset and update DB')
        consolidate(dbdump)

    os.chdir('../')
    if 'export' in module_list:
        logger.info('Export DB')
        exportdb(dbdump)

    os.chdir('./report')
    epiyear, epiweek = episem(date).split('W')
    if epiweek == 1:
        epiyear = int(epiyear) - 1
        epiweek = int(lastepiweek(epiyear))
    else:
        epiyear = int(epiyear)
        epiweek = int(epiweek) - 1

    if 'report' in module_list:
        logger.info('Report generation')
        generate_report(epiyear=epiyear, epiweek=epiweek, plot=plot)

    if 'sendreport' in module_list:
        logger.info('Send report over email')
        send_report_email(epiyear=epiyear, epiweek=epiweek)

    os.chdir('../')

    logger.info('System update: DONE')
    mail_success['email_body'] = mail_success['email_body'] % {'time': time}
    send_email(mail_success)


if __name__ == '__main__':
    today = datetime.datetime.strftime(datetime.datetime.today(), '%Y-%m-%d')

    parser = argparse.ArgumentParser(description="Update InfoGripe database.\n" +
                                                 "python3 update_system.py --mem --path ./data/influ*.DBF\n",
                                     formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument('--mem', action='store_true', help='Update MEM thresholds.')
    parser.add_argument('--modules', nargs='*', action='append',
                        help='Which modules should be ran.\nModule list: %s' % modules_list,
                        default=[])
    parser.add_argument('--path', nargs='*', action='append', help='Path to data file. Optional',
                        default=None)
    parser.add_argument('--history', nargs='*', action='append', help='Path to historical notifications csv files. '
                                                                      'Optional',
                        default=None)
    parser.add_argument('--dir', help='Base folder for e-mail update module. Optional',
                        default=None)
    parser.add_argument('--years', nargs='*', action='append', help='Base years for e-mail update module. Optional',
                        default=None)
    parser.add_argument('--date', help='Base date for estimator in the format YYYY-MM-DD or max. Optional.',
                        default=today)
    parser.add_argument('--dbdump', help='Path do database dump for export. Optional', default=None)
    parser.add_argument('--plot', action='store_true', help='Should the module updat report plots?')

    args = parser.parse_args()
    if args.path:
        args.path = args.path[0]
    if args.modules:
        args.modules = [x.lower() for x in args.modules[0]]
    if args.history:
        args.history = args.history[0]
    if args.years:
        args.years = args.years[0]

    main(flist=args.path, update_mem=args.mem, module_list=args.modules, history_files=args.history, dir=args.dir,
         years=args.years, date=args.date, dbdump=args.dbdump, plot=args.plot)
